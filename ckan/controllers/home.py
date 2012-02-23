import random
import sys

from pylons import config
from pylons.i18n import set_lang
from genshi.template import NewTextTemplate
import sqlalchemy.exc

from ckan.authz import Authorizer
from ckan.logic import NotAuthorized
from ckan.logic import check_access, get_action
from ckan.lib.i18n import set_session_locale, get_lang
from ckan.lib.search import query_for, QueryOptions, SearchError
from ckan.lib.base import *
from ckan.lib.hash import get_redirect
from ckan.lib.helpers import url_for

CACHE_PARAMETER = '__cache'

class HomeController(BaseController):
    repo = model.repo

    def __before__(self, action, **env):
        BaseController.__before__(self, action, **env)
        try:
            context = {'model':model,'user': c.user or c.author}
            check_access('site_read',context)
        except NotAuthorized:
            abort(401, _('Not authorized to see this page'))
        except (sqlalchemy.exc.ProgrammingError,
                sqlalchemy.exc.OperationalError), e:
            # postgres and sqlite errors for missing tables
            msg = str(e)
            if ('relation' in msg and 'does not exist' in msg) or \
                   ('no such table' in msg) :
                # table missing, major database problem
                abort(503, _('This site is currently off-line. Database is not initialised.'))
                # TODO: send an email to the admin person (#1285)
            else:
                raise
            

    def index(self):
        try:
            # package search
            context = {'model': model, 'session': model.Session,
                       'user': c.user or c.author}
            data_dict = {
                'q':'*:*',
                'facet.field':g.facets,
                'rows':0,
                'start':0,
            }
            query = get_action('package_search')(context,data_dict)
            c.package_count = query['count']
            c.facets = query['facets']

            # group search
            data_dict = {'order_by': 'packages', 'all_fields': 1}
            c.groups = get_action('group_list')(context, data_dict)
        except SearchError, se:
            c.package_count = 0
            c.groups = []

        if c.userobj is not None:
            msg = None
            url = url_for(controller='user', action='edit')
            is_google_id = \
                c.userobj.name.startswith('https://www.google.com/accounts/o8/id')
            if not c.userobj.email and (is_google_id and not c.userobj.fullname):
                msg = _('Please <a href="%s">update your profile</a>'
                    ' and add your email address and your full name. ') % url + \
                    _('%s uses your email address'
                      ' if you need to reset your password.') \
                      % g.site_title
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

        return render('home/index.html')

    def license(self):
        return render('home/license.html')

    def about(self):
        return render('home/about.html')
        
    def locale(self): 
        locale = request.params.get('locale')
        if locale is not None:
            try:
                set_session_locale(locale)
            except ValueError:
                abort(400, _('Invalid language specified'))
            if locale == 'en':
                # set_lang('en') causes an exception. Strings are in English
                # anyway, so no need to do it.
                h.flash_notice('Language has been set to: English')
            else:
                set_lang(locale)
                # NOTE: When translating this string, substitute the word
                # 'English' for the language being translated into.
                # We do it this way because some Babel locales don't contain
                # a display_name!
                # e.g. babel.Locale.parse('no').get_display_name() returns None
                h.flash_notice(_('Language has been set to: English'))
        else:
            abort(400, _("No language given!"))
        return_to = get_redirect()
        if not return_to:
            # no need for error, just don't redirect
            return 
        return_to += '&' if '?' in return_to else '?'
        # hack to prevent next page being cached
        return_to += '%s=%s' % (CACHE_PARAMETER, int(random.random()*100000000))
        redirect_to(return_to)

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

