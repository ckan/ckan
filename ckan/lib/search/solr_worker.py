__import__("pkg_resources").get_distribution("ckanext-queue>=0.1")

from ckanext.queue.worker import Worker 
from indexing import index_package, delete_package

class SolrIndexingWorker(Worker):
    
    def consume(self, routing_key, operation, payload):
        assert 'solr_url' in self.config
        assert 'ckan.site_id' in self.config
        
        if routing_key == 'Package':
            if operation in ['new', 'changed']:
                index_package(payload, self.config) 
            elif operation == 'deleted':
                delete_package(payload, self.config) 