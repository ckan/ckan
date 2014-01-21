from pylons import config, cache
import sqlalchemy.exc

import ckan.logic as logic
import ckan.lib.maintain as maintain
import ckan.lib.search as search
import ckan.lib.base as base
import ckan.model as model
import ckan.lib.helpers as h

from ckan.common import _, g, c

CACHE_PARAMETERS = ['__cache', '__no_cache__']

# horrible hack
dirty_cached_group_stuff = None


class HomeController(base.BaseController):
    repo = model.repo

    def __before__(self, action, **env):
        try:
            base.BaseController.__before__(self, action, **env)
            context = {'model': model, 'user': c.user or c.author,
                       'auth_user_obj': c.userobj}
            logic.check_access('site_read', context)
        except logic.NotAuthorized:
            base.abort(401, _('Not authorized to see this page'))
        except (sqlalchemy.exc.ProgrammingError,
                sqlalchemy.exc.OperationalError), e:
            # postgres and sqlite errors for missing tables
            msg = str(e)
            if ('relation' in msg and 'does not exist' in msg) or \
                    ('no such table' in msg):
                # table missing, major database problem
                base.abort(503, _('This site is currently off-line. Database '
                                  'is not initialised.'))
                # TODO: send an email to the admin person (#1285)
            else:
                raise

    def index(self):
        try:
            # package search
            context = {'model': model, 'session': model.Session,
                       'user': c.user or c.author, 'auth_user_obj': c.userobj}
            data_dict = {
                'q': '*:*',
                'facet.field': g.facets,
                'rows': 4,
                'start': 0,
                'sort': 'views_recent desc',
                'fq': 'capacity:"public"'
            }
            query = logic.get_action('package_search')(
                context, data_dict)
            c.search_facets = query['search_facets']
            c.package_count = query['count']
            c.datasets = query['results']

            c.facets = query['facets']
            maintain.deprecate_context_item(
                'facets',
                'Use `c.search_facets` instead.')

            c.search_facets = query['search_facets']

            c.facet_titles = {
                'organization': _('Organizations'),
                'groups': _('Groups'),
                'tags': _('Tags'),
                'res_format': _('Formats'),
                'license': _('Licenses'),
            }

            data_dict = {'sort': 'packages', 'all_fields': 1}
            # only give the terms to group dictize that are returned in the
            # facets as full results take a lot longer
            if 'groups' in c.search_facets:
                data_dict['groups'] = [
                    item['name'] for item in c.search_facets['groups']['items']
                ]
            c.groups = logic.get_action('group_list')(context, data_dict)
        except search.SearchError:
            c.package_count = 0
            c.groups = []

        if c.userobj is not None:
            msg = None
            url = h.url_for(controller='user', action='edit')
            is_google_id = \
                c.userobj.name.startswith(
                    'https://www.google.com/accounts/o8/id')
            if not c.userobj.email and (is_google_id and
                                        not c.userobj.fullname):
                msg = _(u'Please <a href="{link}">update your profile</a>'
                        u' and add your email address and your full name. '
                        u'{site} uses your email address'
                        u' if you need to reset your password.'.format(
                            link=url, site=g.site_title))
            elif not c.userobj.email:
                msg = _('Please <a href="%s">update your profile</a>'
                        ' and add your email address. ') % url + \
                    _('%s uses your email address'
                        ' if you need to reset your password.') \
                    % g.site_title
            elif is_google_id and not c.userobj.fullname:
                msg = _('Please <a href="%s">update your profile</a>'
                        ' and add your full name.') % (url)
            if msg:
                h.flash_notice(msg, allow_html=True)

        # START OF DIRTYNESS
        def get_group(id):
            def _get_group_type(id):
                """
                Given the id of a group it determines the type of a group given
                a valid id/name for the group.
                """
                group = model.Group.get(id)
                if not group:
                    return None
                return group.type

            def db_to_form_schema(group_type=None):
                from ckan.lib.plugins import lookup_group_plugin
                return lookup_group_plugin(group_type).db_to_form_schema()

            group_type = _get_group_type(id.split('@')[0])
            context = {'model': model, 'session': model.Session,
                       'ignore_auth': True,
                       'user': c.user or c.author,
                       'auth_user_obj': c.userobj,
                       'schema': db_to_form_schema(group_type=group_type),
                       'limits': {'packages': 2},
                       'for_view': True}
            data_dict = {'id': id}

            try:
                group_dict = logic.get_action('group_show')(context, data_dict)
            except logic.NotFound:
                return None

            return {'group_dict': group_dict}

        global dirty_cached_group_stuff
        if not dirty_cached_group_stuff:
            groups_data = []
            groups = config.get('ckan.featured_groups', '').split()

            for group_name in groups:
                group = get_group(group_name)
                if group:
                    groups_data.append(group)
                if len(groups_data) == 2:
                    break

            # c.groups is from the solr query above
            if len(groups_data) < 2 and len(c.groups) > 0:
                group = get_group(c.groups[0]['name'])
                if group:
                    groups_data.append(group)
            if len(groups_data) < 2 and len(c.groups) > 1:
                group = get_group(c.groups[1]['name'])
                if group:
                    groups_data.append(group)
            # We get all the packages or at least too many so
            # limit it to just 2
            for group in groups_data:
                group['group_dict']['packages'] = \
                    group['group_dict']['packages'][:2]
            #now add blanks so we have two
            while len(groups_data) < 2:
                groups_data.append({'group_dict': {}})
            # cache for later use
            dirty_cached_group_stuff = groups_data

        c.group_package_stuff = dirty_cached_group_stuff

        # END OF DIRTYNESS

        return base.render('home/index.html', cache_force=True)

    def license(self):
        return base.render('home/license.html')

    def about(self):
        return base.render('home/about.html')

    def cache(self, id):
        '''Manual way to clear the caches'''
        if id == 'clear':
            wui_caches = ['stats']
            for cache_name in wui_caches:
                cache_ = cache.get_cache(cache_name, type='dbm')
                cache_.clear()
            return 'Cleared caches: %s' % ', '.join(wui_caches)

    def cors_options(self, url=None):
        # just return 200 OK and empty data
        return ''
