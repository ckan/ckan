# encoding: utf-8

from pylons import cache
import sqlalchemy.exc

import ckan.logic as logic
import ckan.lib.search as search
import ckan.lib.base as base
import ckan.model as model
import ckan.lib.helpers as h

from ckan.common import _, config, c

CACHE_PARAMETERS = ['__cache', '__no_cache__']


class HomeController(base.BaseController):
    repo = model.repo

    def __before__(self, action, **env):
        try:
            base.BaseController.__before__(self, action, **env)
            context = {'model': model, 'user': c.user,
                       'auth_user_obj': c.userobj}
            logic.check_access('site_read', context)
        except logic.NotAuthorized:
            base.abort(403, _('Not authorized to see this page'))
        except (sqlalchemy.exc.ProgrammingError,
                sqlalchemy.exc.OperationalError) as e:
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
                       'user': c.user, 'auth_user_obj': c.userobj}
            data_dict = {
                'q': '*:*',
                'facet.field': h.facets(),
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

            c.facet_titles = {
                'organization': _('Organizations'),
                'groups': _('Groups'),
                'tags': _('Tags'),
                'res_format': _('Formats'),
                'license': _('Licenses'),
            }

        except search.SearchError:
            c.package_count = 0

        if c.userobj and not c.userobj.email:
            url = h.url_for('user.edit')
            msg = _('Please <a href="%s">update your profile</a>'
                    ' and add your email address. ') % url + \
                _('%s uses your email address'
                    ' if you need to reset your password.') \
                % config.get('ckan.site_title')
            h.flash_notice(msg, allow_html=True)

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
