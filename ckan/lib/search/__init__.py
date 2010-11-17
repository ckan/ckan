import logging
import pkg_resources
from pylons import config
from common import QueryOptions, SearchError
from worker import dispatch_by_operation

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
    'search_tags': True,
    'callback': None, # simply passed through
    }

# TODO make sure all backends are thread-safe! 
INSTANCE_CACHE = {}

def get_backend(backend=None):
    if backend is None:
        backend = config.get('search_backend', 'sql')
    klass = None
    for ep in pkg_resources.iter_entry_points("ckan.search", backend.strip().lower()):
        klass = ep.load()
    if klass is None:
        raise KeyError("No search backend called %s" % (backend,))
    if not klass in INSTANCE_CACHE.keys():
        log.debug("Creating search backend: %s" % klass.__name__)
        INSTANCE_CACHE[klass] = klass()
    return INSTANCE_CACHE.get(klass)

def rebuild():
    from ckan import model
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



    
