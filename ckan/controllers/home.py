import random

from pylons.i18n import set_lang
import sqlalchemy.exc

import ckan.logic
import ckan.lib.maintain as maintain
from ckan.lib.search import SearchError
from ckan.lib.base import *
from ckan.lib.helpers import url_for

CACHE_PARAMETER = '__cache'


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
                'rows': 0,
                'start': 0,
                'fq': 'capacity:"public"'
            }
            query = ckan.logic.get_action('package_search')(
                context, data_dict)
            c.package_count = query['count']

            c.facets = query['facets']
            maintain.deprecate_context_item(
              'facets',
              'Use `c.search_facets` instead.')

            c.search_facets = query['search_facets']

            data_dict = {'order_by': 'packages', 'all_fields': 1}
            # only give the terms to group dictize that are returned in the
            # facets as full results take a lot longer
            if 'groups' in c.search_facets:
                data_dict['groups'] = [ item['name'] for item in
                    c.search_facets['groups']['items'] ]
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
                msg = _(u'Please <a href="{link}">update your profile</a>'
                        u' and add your email address and your full name. '
                        u'{site} uses your email address'
                        u' if you need to reset your password.'.format(link=url,
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
