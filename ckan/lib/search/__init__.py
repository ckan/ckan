import logging

from pylons import config
from ckan import model
from common import QueryOptions
from sql import SqlSearchBackend
from solr_ import SolrSearchBackend
from worker import SearchIndexWorker, setup_synchronous_indexing, remove_synchronous_indexing

log = logging.getLogger(__name__)

DEFAULT_OPTIONS = {
    'limit': 20,
    'offset': 0,
    'filter_by_openness': False,
    'filter_by_downloadable': False,
    # about presenting the results
    'order_by': 'rank',
    'return_objects': False,
    'ref_entity_with_attr': 'name',
    'all_fields': False,
    'search_tags': True}

BACKENDS = {
    'sql': SqlSearchBackend,
    'solr': SolrSearchBackend
    }

# TODO make sure all backends are thread-safe! 
INSTANCE_CACHE = {}

def get_backend(backend=None):
    if backend is None:
        backend = config.get('search_backend', 'sql')
    klass = BACKENDS.get(backend.strip().lower())
    if not klass in INSTANCE_CACHE.keys():
        log.debug("Creating search backend: %s" % klass.__name__)
        INSTANCE_CACHE[klass] = klass()
    return INSTANCE_CACHE.get(klass)

def rebuild():
    backend = get_backend()
    log.debug("Rebuilding search index...")
    
    # Packages
    package_index = backend.index_for(model.Package)
    package_index.clear()
    for pkg in model.Session.query(model.Package).all():
        package_index.insert_entity(pkg)

def query_for(_type, backend=None):
    """ Query for entities of a specified type (name, class, instance). """
    return get_backend(backend=backend).query_for(_type)



    