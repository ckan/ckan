import random
import sys

from pylons import cache, config
from genshi.template import NewTextTemplate

from ckan.authz import Authorizer
from ckan.i18n import set_session_locale
from ckan.lib.search import query_for, QueryOptions, SearchError
from ckan.lib.cache import proxy_cache, get_cache_expires
from ckan.lib.base import *
import ckan.lib.stats
import ckan.lib.hash

cache_expires = get_cache_expires(sys.modules[__name__])

class HomeController(BaseController):
    repo = model.repo   

    authorizer = Authorizer()

    @proxy_cache(expires=cache_expires)
    def index(self):
        query = query_for(model.Package)
        query.run(query='*:*', facet_by=g.facets,
                  limit=0, offset=0, username=c.user)
        c.facets = query.facets
        c.fields = []
        c.package_count = query.count
        c.latest_packages = self.authorizer.authorized_query(c.user, model.Package)\
            .join('revision').order_by(model.Revision.timestamp.desc())\
            .limit(5).all()

        if len(c.latest_packages):
            cache_key = str(hash((c.latest_packages[0].id, c.user)))
        else:
            cache_key = "fresh-install"
        
        etag_cache(cache_key)
        return render('home/index.html', cache_key=cache_key,
                cache_expire=cache_expires)

    def license(self):
        return render('home/license.html', cache_expire=cache_expires)

    def about(self):
        return render('home/about.html', cache_expire=cache_expires)
        
    def language(self):
        response.content_type = 'text/json'
        return render('home/language.js', cache_expire=cache_expires,
                      method='text', loader_class=NewTextTemplate)
    
    def locale(self): 
        return_to = request.params.get('return_to', '/')
        hash_given = request.params.get('hash', '')
        locale = request.params.get('locale')
        if locale is not None:
            h.flash_notice(_("Language has been set to: English"))
            set_session_locale(locale)
        else:
            h.flash_notice(_("No language given!"))
        hash_expected = ckan.lib.hash.get_message_hash(return_to)
        if hash_given != hash_expected:
            # no need for error, just don't redirect
            return 
        return_to += '&' if '?' in return_to else '?'
        # hack to prevent next page being cached
        return_to += '__cache=%s' %  int(random.random()*100000000)
        redirect_to(return_to.encode('utf-8'))

    def cache(self, id):
        '''Manual way to clear the caches'''
        if id == 'clear':
            wui_caches = ['tag_counts', 'search_results', 'stats']
            for cache_name in wui_caches:
                cache_ = cache.get_cache(cache_name, type='dbm')
                cache_.clear()
            return 'Cleared caches: %s' % ', '.join(wui_caches)

