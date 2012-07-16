import random

from pylons.i18n import set_lang
import sqlalchemy.exc

import ckan.logic
from ckan.lib.search import SearchError
from ckan.lib.base import *
from ckan.lib.helpers import url_for

CACHE_PARAMETERS = ['__cache', '__no_cache__']

# horrible hack
dirty_cached_group_stuff = None

class HomeController(BaseController):
    repo = model.repo

    def __before__(self, action, **env):
        try:
            BaseController.__before__(self, action, **env)
            context = {'model': model, 'user': c.user or c.author}
            ckan.logic.check_access('site_read', context)
        except ckan.logic.NotAuthorized:
            abort(401, _('Not authorized to see this page'))
        except (sqlalchemy.exc.ProgrammingError,
                sqlalchemy.exc.OperationalError), e:
            # postgres and sqlite errors for missing tables
            msg = str(e)
            if ('relation' in msg and 'does not exist' in msg) or \
                    ('no such table' in msg):
                # table missing, major database problem
                abort(503, _('This site is currently off-line. Database '
                             'is not initialised.'))
                # TODO: send an email to the admin person (#1285)
            else:
                raise

    def index(self):
        try:
            # package search
            context = {'model': model, 'session': model.Session,
                       'user': c.user or c.author}
            data_dict = {
                'q': '*:*',
                'facet.field': g.facets,
                'rows': 4,
                'start': 0,
                'sort': 'views_recent desc',
                'fq': 'capacity:"public"'
            }
            query = ckan.logic.get_action('package_search')(
                context, data_dict)
            c.search_facets = query['search_facets']
            c.package_count = query['count']
            c.datasets = query['results']
            c.facets = query['facets']
            c.facet_titles = {'groups': _('Groups'),
                          'tags': _('Tags'),
                          'res_format': _('Formats'),
                          'license': _('Licence'), }

            data_dict = {'order_by': 'packages', 'all_fields': 1}
            # only give the terms to group dictize that are returned in the
            # facets as full results take a lot longer
            if 'groups' in c.facets:
                data_dict['groups'] = c.facets['groups'].keys()
            c.groups = ckan.logic.get_action('group_list')(context, data_dict)
        except SearchError, se:
            c.package_count = 0
            c.groups = []

        if c.userobj is not None:
            msg = None
            url = url_for(controller='user', action='edit')
            is_google_id = \
                c.userobj.name.startswith(
                    'https://www.google.com/accounts/o8/id')
            if not c.userobj.email and (is_google_id and
                                        not c.userobj.fullname):
                msg = _('Please <a href="{link}">update your profile</a>'
                        ' and add your email address and your full name. '
                        '{site} uses your email address'
                        ' if you need to reset your password.'.format(link=url,
                        site=g.site_title))
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

        c.recently_changed_packages_activity_stream = \
            ckan.logic.action.get.recently_changed_packages_activity_list_html(
                context, {})

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

            def _form_to_db_schema(group_type=None):
                from ckan.lib.plugins import lookup_group_plugin
                return lookup_group_plugin(group_type).form_to_db_schema()

            group_type = _get_group_type(id.split('@')[0])
            context = {'model': model, 'session': model.Session,
                       'user': c.user or c.author,
                       'schema': _form_to_db_schema(group_type=group_type),
                       'for_view': True}
            data_dict = {'id': id}

            try:
                group_dict = ckan.logic.get_action('group_show')(context, data_dict)
            except ckan.logic.NotFound:
                return {'group_dict' :{}}

            # We get all the packages or at least too many so
            # limit it to just 2
            group_dict['packages'] = group_dict['packages'][:2]
            return {'group_dict' :group_dict}

        global dirty_cached_group_stuff
        if not dirty_cached_group_stuff:
            # ARON
            # uncomment the first for testing
            # the second for demo - different data
            #dirty_cached_group_stuff = [get_group('access-to-medicines'), get_group('archaeology')]
            dirty_cached_group_stuff = [get_group('data-explorer'), get_group('geo-examples')]

        c.group_package_stuff = dirty_cached_group_stuff
        # END OF DIRTYNESS

        return render('home/index.html', cache_force=True)

    def license(self):
        return render('home/license.html')

    def about(self):
        return render('home/about.html')

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
