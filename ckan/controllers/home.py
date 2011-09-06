import random
import sys

from pylons import cache, config
from genshi.template import NewTextTemplate

from ckan.authz import Authorizer
from ckan.logic.action.get import current_package_list_with_resources
from ckan.i18n import set_session_locale, set_lang
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
        if not self.authorizer.am_authorized(c, model.Action.SITE_READ, model.System):
            abort(401, _('Not authorized to see this page'))

    @staticmethod
    def _home_cache_key(latest_revision_id=None):
        '''Calculate the etag cache key for the home page. If you have
        the latest revision id then supply it as a param.'''
        if not latest_revision_id:
            latest_revision_id = model.repo.youngest_revision().id
        user_name = c.user
        if latest_revision_id:
            cache_key = str(hash((latest_revision_id, user_name)))
        else:
            cache_key = 'fresh-install'
        return cache_key

    @proxy_cache(expires=cache_expires)
    def index(self):
        cache_key = self._home_cache_key()
        etag_cache(cache_key)

        query = query_for(model.Package)
        query.run(query='*:*', facet_by=g.facets,
                  limit=0, offset=0, username=c.user,
                  order_by=None)
        c.facets = query.facets
        c.fields = []
        c.package_count = query.count
        c.latest_packages = current_package_list_with_resources({'model': model,
                                                                 'user': c.user},
                                                                 {'limit': 5})      
        return render('home/index.html', cache_key=cache_key,
                      cache_expire=cache_expires)

    def license(self):
        return render('home/license.html', cache_expire=cache_expires)

    def about(self):
        return render('home/about.html', cache_expire=cache_expires)
        
    def language(self):
        response.content_type = 'text/javascript'
        return render('home/language.js', cache_expire=cache_expires,
                      method='text', loader_class=NewTextTemplate)
    
    def locale(self): 
        locale = request.params.get('locale')
        if locale is not None:
            try:
                set_session_locale(locale)
            except ValueError:
                abort(400, _('Invalid language specified'))
            try:
                set_lang(locale)
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

