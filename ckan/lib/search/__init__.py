import logging
from pylons import config

from ckan import model
from ckan.model import DomainObjectOperation
from ckan.plugins import SingletonPlugin, implements, IDomainObjectModification
from ckan.lib.dictization.model_dictize import package_to_api1
from common import SearchIndexError, SearchError, make_connection, is_available, DEFAULT_SOLR_URL
from index import PackageSearchIndex, NoopSearchIndex
from query import TagSearchQuery, ResourceSearchQuery, PackageSearchQuery, QueryOptions, convert_legacy_parameters_to_solr

log = logging.getLogger(__name__)

SIMPLE_SEARCH = config.get('ckan.simple_search', False)

DEFAULT_OPTIONS = {
    'limit': 20,
    'offset': 0,
    # about presenting the results
    'order_by': 'rank',
    'return_objects': False,
    'ref_entity_with_attr': 'name',
    'all_fields': False,
    'search_tags': True,
    'callback': None, # simply passed through
}

_INDICES = {
    'package': PackageSearchIndex
}

_QUERIES = {
    'tag': TagSearchQuery,
    'resource': ResourceSearchQuery,
    'package': PackageSearchQuery
}

if SIMPLE_SEARCH:
    import sql as sql
    _INDICES['package'] = NoopSearchIndex
    _QUERIES['package'] = sql.PackageSearchQuery

def _normalize_type(_type):
    if isinstance(_type, model.DomainObject):
        _type = _type.__class__
    if isinstance(_type, type):
        _type = _type.__name__
    return _type.strip().lower()

def index_for(_type):
    """ Get a SearchIndex instance sub-class suitable for the specified type. """
    try:
        _type_n = _normalize_type(_type)
        return _INDICES[_type_n]()
    except KeyError, ke:
        log.warn("Unknown search type: %s" % _type)
        return NoopSearchIndex()

def query_for( _type):
    """ Get a SearchQuery instance sub-class suitable for the specified type. """
    try:
        _type_n = _normalize_type(_type)
        return _QUERIES[_type_n]()
    except KeyError, ke:
        raise SearchError("Unknown search type: %s" % _type)

def dispatch_by_operation(entity_type, entity, operation):
    """Call the appropriate index method for a given notification."""
    try:
        index = index_for(entity_type)
        if operation == DomainObjectOperation.new:
            index.insert_dict(entity)
        elif operation == DomainObjectOperation.changed:
            index.update_dict(entity)
        elif operation == DomainObjectOperation.deleted:
            index.remove_dict(entity)
        else:
            log.warn("Unknown operation: %s" % operation)
    except Exception, ex:
        log.exception(ex)
        # we really need to know about any exceptions, so reraise
        # (see #1172)
        raise
        

class SynchronousSearchPlugin(SingletonPlugin):
    """Update the search index automatically."""
    implements(IDomainObjectModification, inherit=True)

    def notify(self, entity, operation):
        if operation != DomainObjectOperation.deleted:
            dispatch_by_operation(entity.__class__.__name__, 
                                  package_to_api1(entity, {'model': model}),
                                  operation)
        elif operation == DomainObjectOperation.deleted:
            dispatch_by_operation(entity.__class__.__name__, 
                                  {'id': entity.id}, operation)
        else:
            log.warn("Discarded Sync. indexing for: %s" % entity)

def rebuild():
    from ckan import model
    log.debug("Rebuilding search index...")
    
    # Packages
    package_index = index_for(model.Package)
    package_index.clear()
    for pkg in model.Session.query(model.Package).all():
        package_index.insert_entity(pkg)
    model.Session.commit()

def check():
    from ckan import model
    package_query = query_for(model.Package)

    log.debug("Checking packages search index...")
    pkgs_q = model.Session.query(model.Package).filter_by(state=model.State.ACTIVE)
    pkgs = set([pkg.id for pkg in pkgs_q])
    indexed_pkgs = set(package_query.get_all_entity_ids(max_results=len(pkgs)))
    pkgs_not_indexed = pkgs - indexed_pkgs
    print 'Packages not indexed = %i out of %i' % (len(pkgs_not_indexed), len(pkgs))
    for pkg_id in pkgs_not_indexed:
        pkg = model.Session.query(model.Package).get(pkg_id)
        print pkg.revision.timestamp.strftime('%Y-%m-%d'), pkg.name

def show(package_reference):
    from ckan import model
    package_index = index_for(model.Package)
    print package_index.get_index(package_reference)

def clear():
    from ckan import model
    log.debug("Clearing search index...")
    package_index = index_for(model.Package)
    package_index.clear()
