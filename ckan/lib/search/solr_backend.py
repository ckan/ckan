from pylons import config
from ckan.lib.search import SearchBackend, SearchQuery, SearchIndex, \
    SearchError
from ckan.authz import Authorizer
from ckan import model
from solr_indexing import make_connection, index_package, delete_package, \
    clear_index
import logging
log = logging.getLogger(__name__)


class SolrSearchBackend(SearchBackend):
    
    def _setup(self):
        self.register(model.Package.__name__, PackageSolrSearchIndex, PackageSolrSearchQuery)    

class PackageSolrSearchQuery(SearchQuery):
    
    def _run(self):
        fq = ""

        # Filter for options
        if self.options.filter_by_downloadable:
            fq += u" +res_url:[* TO *] " # not null resource URL 
        if self.options.filter_by_openness:
            licenses = ["license_id:%s" % id for id in self.open_licenses]
            licenses = " OR ".join(licenses)
            fq += " +(%s) " % licenses
        
        order_by = self.options.order_by
        if order_by == 'rank' or order_by is None: 
            order_by = 'score'

        # show only results from this CKAN instance:
        fq = fq + " +site_id:\"%s\" " % config.get('ckan.site_id')

        # Filter for package status       
        fq += "+state:active "
            
        # configurable for iati: full options list
        facet_limit = int(config.get('search.facets.limit', '50'))

        # query
        query = self.query.query
        if (not query) or (not query.strip()):
            # no query terms, i.e. all documents
            query = '*:*'
        
        conn = make_connection(config)
        try:
            data = conn.query(query,
                              fq=fq, 
                              # make sure data.facet_counts is set:
                              facet='true',
                              facet_limit=facet_limit,
                              facet_field=self.facet_by,
                              facet_mincount=1,
                              start=self.options.offset, 
                              rows=self.options.limit,
                              fields='id,score', 
                              sort_order='desc', 
                              sort=order_by)
            
        except Exception, e:
            # this wrapping will be caught further up in the WUI.
            log.exception(e)
            raise SearchError(e)
        finally:
            conn.close()
        
        self.count = int(data.numFound)
        scores = dict([(r.get('id'), r.get('score')) for r in data.results])
        q = Authorizer().authorized_query(self.options.username, model.Package)
        q = q.filter(model.Package.id.in_(scores.keys()))
        self.facets = data.facet_counts.get('facet_fields', {})
        self.results = sorted(q, key=lambda r: scores[r.id], reverse=True)

    
class SolrSearchIndex(SearchIndex):
    
    def clear(self):
        clear_index(config)

class PackageSolrSearchIndex(SolrSearchIndex):
    
    def remove_dict(self, pkg_dict):
        delete_package(pkg_dict, config)
    
    def update_dict(self, pkg_dict):
        index_package(pkg_dict, config)
