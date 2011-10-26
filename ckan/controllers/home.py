import random
import sys

from pylons import cache, config
from pylons.i18n import set_lang
from genshi.template import NewTextTemplate
import sqlalchemy.exc

from ckan.authz import Authorizer
from ckan.logic import NotAuthorized
from ckan.logic import check_access, get_action
from ckan.lib.i18n import set_session_locale, get_lang
from ckan.lib.search import query_for, QueryOptions, SearchError
from ckan.lib.cache import proxy_cache, get_cache_expires
from ckan.lib.base import *
import ckan.lib.stats
from ckan.lib.hash import get_redirect

cache_expires = get_cache_expires(sys.modules[__name__])

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
            

    @staticmethod
    def _home_cache_key():
        '''Calculate the etag cache key for the home page.'''
        # a change to the data means the group package amounts may change
        latest_revision_id = model.repo.youngest_revision().id
        user_name = c.user
        language = get_lang()
        cache_key = str(hash((user_name, language, latest_revision_id)))
        return cache_key

    @proxy_cache(expires=cache_expires)
    def index(self):
        cache_key = self._home_cache_key()
        etag_cache(cache_key)

        try:
            query = query_for(model.Package)
            query.run({'q': '*:*', 'facet.field': g.facets})
            c.package_count = query.count
            c.facets = query.facets # used by the 'tag cloud' recipe
            q = model.Session.query(model.Group).filter_by(state='active')
            c.groups = sorted(q.all(), key=lambda g: len(g.packages), reverse=True)[:6]
        except SearchError, se:
            c.package_count = 0
            c.groups = []

        return render('home/index.html', cache_key=cache_key,
                      cache_expire=cache_expires)

    def license(self):
        return render('home/license.html', cache_expire=cache_expires)

    def about(self):
        return render('home/about.html', cache_expire=cache_expires)
        
    def locale(self): 
        locale = request.params.get('locale')
        if locale is not None:
            try:
                set_session_locale(locale)
            except ValueError:
                abort(400, _('Invalid language specified'))
            try:
                set_lang(locale)
                # NOTE: When translating this string, substitute the word
                # 'English' for the language being translated into.
                # We do it this way because some Babel locales don't contain
                # a display_name!
                # e.g. babel.Locale.parse('no').get_display_name() returns None
                h.flash_notice(_("Language has been set to: English"))
            except:
                h.flash_notice("Language has been set to: English")
        else:
            abort(400, _("No language given!"))
        return_to = get_redirect()
        if not return_to:
            # no need for error, just don't redirect
            return 
        return_to += '&' if '?' in return_to else '?'
        # hack to prevent next page being cached
        return_to += '__cache=%s' %  int(random.random()*100000000)
        redirect_to(return_to)

    def cache(self, id):
        '''Manual way to clear the caches'''
        if id == 'clear':
            wui_caches = ['tag_counts', 'search_results', 'stats']
            for cache_name in wui_caches:
                cache_ = cache.get_cache(cache_name, type='dbm')
                cache_.clear()
            return 'Cleared caches: %s' % ', '.join(wui_caches)

    def cors_options(self, url=None):
        # just return 200 OK and empty data
        return ''

