from pylons import config
import logging
log = logging.getLogger(__name__)


class SearchIndexError(Exception):
    pass


class SearchError(Exception):
    pass


class SearchQueryError(SearchError):
    pass

DEFAULT_SOLR_URL = 'http://127.0.0.1:8983/solr'


class SolrSettings(object):
    _is_initialised = False
    _url = None
    _user = None
    _password = None

    @classmethod
    def init(cls, url, user=None, password=None):
        if url is not None:
            cls._url = url
            cls._user = user
            cls._password = password
        else:
            cls._url = DEFAULT_SOLR_URL
        cls._is_initialised = True

    @classmethod
    def get(cls):
        if not cls._is_initialised:
            raise SearchIndexError('SOLR URL not initialised')
        if not cls._url:
            raise SearchIndexError('SOLR URL is blank')
        return (cls._url, cls._user, cls._password)


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
        if 'conn' in dir():
            conn.close()

    return True


def make_connection():
    from solr import SolrConnection
    solr_url, solr_user, solr_password = SolrSettings.get()
    assert solr_url is not None
    if solr_user is not None and solr_password is not None:
        return SolrConnection(solr_url, http_user=solr_user,
                              http_pass=solr_password)
    else:
        return SolrConnection(solr_url)
