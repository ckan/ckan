from pylons import config
import logging
log = logging.getLogger(__name__)

class SearchIndexError(Exception): pass
class SearchError(Exception): pass
class SearchQueryError(SearchError): pass

DEFAULT_SOLR_URL = 'http://127.0.0.1:8983/solr'

solr_url = config.get('solr_url', DEFAULT_SOLR_URL)
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

def make_connection():
    from solr import SolrConnection
    if solr_user is not None and solr_password is not None:
        return SolrConnection(solr_url, http_user=solr_user, http_pass=solr_password)
    else:
        return SolrConnection(solr_url)
