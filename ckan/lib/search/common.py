from solr import SolrConnection
import logging
log = logging.getLogger(__name__)

class SearchError(Exception): pass

def make_connection(config):
    url = config.get('solr_url', 'http://localhost:8983/solr')
    user = config.get('solr_user')
    password = config.get('solr_password')

    if user is not None and password is not None:
        return SolrConnection(url, http_user=user, http_pass=password)
    else:
        return SolrConnection(url)
