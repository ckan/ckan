import logging

from pylons import config
from common import SearchBackend, SearchQuery, SearchIndex, SearchError
from ckan import model, authz
from ckan.model import meta


log = logging.getLogger(__name__)

TYPE_FIELD = "entity_type"
SOLR_FIELDS = [TYPE_FIELD, "res_url", "text", "urls", "indexed_ts", "site_id"]

class SolrSearchBackend(SearchBackend):
    
    def _setup(self):
        # import inline to avoid external dependency 
        from solr import SolrConnection # == solrpy 
        solr_url = config.get('solr_url', 'http://localhost:8983/solr')
        solr_user = config.get('solr_user')
        solr_password = config.get('solr_password')
        if solr_user is not None and solr_password is not None:
            self.connection = SolrConnection(solr_url, http_user=solr_user, http_pass=solr_password)
        else:
            self.connection = SolrConnection(solr_url)
        
        self.register(model.Package.__name__, PackageSolrSearchIndex, PackageSolrSearchQuery)
        
        
class PackageSolrSearchQuery(SearchQuery):
    
    def _run(self):
        query = ""
        
        #if not self.options.get('search_tags', True):
        # TODO: figure out how to handle this without messing with the query parser too much    
        
        # Filter for options
        if self.options.filter_by_downloadable:
            query += u" +res_url:[* TO *] " # not null resource URL 
        if self.options.filter_by_openness:
            licenses = ["license_id:%s" % id for id in self.open_licenses]
            licenses = " OR ".join(licenses)
            query += " +(%s) " % licenses
        
        order_by = self.options.order_by
        if order_by == 'rank': order_by = 'score'
        
        # show only results from this CKAN instance:
        query = query + " +site_id:%s" % config.get('ckan.site_id')
        
        data = self.backend.connection.query(self.query.query,
                                       fq=query, 
                                       start=self.options.offset, 
                                       rows=self.options.limit,
                                       fields='id,score', 
                                       sort_order='desc', 
                                       sort=order_by)
        
        self.count = int(data.numFound)
        result_ids = [(r.get('id')) for r in data.results]
        q = authz.Authorizer().authorized_query(self.options.username, model.Package)
        q = q.filter(model.Package.id.in_(result_ids))
        self.results = q.all()

    
class SolrSearchIndex(SearchIndex):
    
    TYPE = u"undefined"
    
    def remove_dict(self, data):
        if not 'id' in data:
            raise SearchError("No ID for record deletion")
        query = "+%s:%s +id:%s +site_id:%s" % (TYPE_FIELD, self.TYPE, data.get('id'), config.get('ckan.site_id'))
        self.backend.connection.delete_query(query)
        self.backend.connection.commit()
        
    def clear(self):
        query = "+%s:%s +site_id:%s" % (TYPE_FIELD, self.TYPE, config.get('ckan.site_id'))
        self.backend.connection.delete_query(query)
        self.backend.connection.commit()


class PackageSolrSearchIndex(SolrSearchIndex):
    
    TYPE = u'package'
    RESERVED_FIELDS = SOLR_FIELDS + ["tags", "groups", "res_description", 
                                     "res_format", "res_url"]
    
    def update_dict(self, pkg_dict):
        index_fields = self.RESERVED_FIELDS + pkg_dict.keys()
            
        # include the extras in the main namespace
        extras = pkg_dict.get('extras', {})
        if 'extras' in pkg_dict:
            del pkg_dict['extras']
        for (key, value) in extras.items():
            if key not in index_fields:
                pkg_dict[key] = value

        # flatten the structure for indexing: 
        for resource in pkg_dict.get('resources', []):
            for (okey, nkey) in [('description', 'res_description'),
                                 ('format', 'res_format'),
                                 ('url', 'res_url')]:
                pkg_dict[nkey] = pkg_dict.get(nkey, []) + [resource.get(okey, u'')]
        if 'resources' in pkg_dict:
            del pkg_dict['resources']

        pkg_dict[TYPE_FIELD] = self.TYPE
        pkg_dict = dict([(str(k), v) for (k, v) in pkg_dict.items()])
        
        # mark this CKAN instance as data source:
        pkg_dict['site_id'] = config.get('ckan.site_id')
        
        # send to solr:    
        self.backend.connection.add(**pkg_dict)
        self.backend.connection.commit()
        log.debug("Updated index for %s" % pkg_dict.get('name'))
