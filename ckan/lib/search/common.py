from pylons import config
from solr import SolrConnection
import logging
log = logging.getLogger(__name__)

class SearchError(Exception): pass

def is_available():
    """
    Return true if we can successfully connect to Solr.
    """
    try:
        conn = make_connection(config)
        conn.query("*:*", rows=1)
        conn.close()
    except Exception, e:
        log.exception(e)
        return False

    return True

def is_enabled():
    """
    Return true if search is enabled in ckan config.
    """
    return config.get('search_enabled')

def make_connection(config):
    url = config.get('solr_url', 'http://localhost:8983/solr')
    user = config.get('solr_user')
    password = config.get('solr_password')

    if user is not None and password is not None:
        return SolrConnection(url, http_user=user, http_pass=password)
    else:
        return SolrConnection(url)
