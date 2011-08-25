from pylons import config
from solr import SolrConnection
import logging
log = logging.getLogger(__name__)

class SearchIndexError(Exception): pass
class SearchError(Exception): pass

solr_url = config.get('solr_url', 'http://127.0.0.1:8983/solr')
solr_user = config.get('solr_user')
solr_password = config.get('solr_password')

def is_available():
    """
    Return true if we can successfully connect to Solr.
    """
    try:
        conn = make_connection()
        conn.query("*:*", rows=1)
    except Exception, e:
        log.exception(e)
        return False
    finally:
        conn.close()

    return True

def is_enabled():
    """
    Return true if search is enabled in ckan config.
    """
    return config.get('search_enabled', True)

def make_connection():
    if solr_user is not None and solr_password is not None:
        return SolrConnection(solr_url, http_user=solr_user, http_pass=solr_password)
    else:
        return SolrConnection(solr_url)
