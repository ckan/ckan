import socket
import string
import logging
import itertools

from pylons import config

from common import SearchIndexError, make_connection

log = logging.getLogger(__name__)

TYPE_FIELD = "entity_type"
PACKAGE_TYPE = "package"
KEY_CHARS = string.digits + string.letters + "_-"
SOLR_FIELDS = [TYPE_FIELD, "res_url", "text", "urls", "indexed_ts", "site_id"]
RESERVED_FIELDS = SOLR_FIELDS + ["tags", "groups", "res_description", 
                                 "res_format", "res_url"]
# HACK: this is copied over from model.PackageRelationship 
RELATIONSHIP_TYPES = [
    (u'depends_on', u'dependency_of'),
    (u'derives_from', u'has_derivation'),
    (u'links_to', u'linked_from'),
    (u'child_of', u'parent_of'),
]

def clear_index():
    conn = make_connection()
    query = "+site_id:\"%s\"" % (config.get('ckan.site_id'))
    try:
        conn.delete_query(query)
        conn.commit()
    except socket.error, e:
        log.error('Could not connect to SOLR: %r' % e)
        raise
    finally:
        conn.close()

class SearchIndex(object):
    """ 
    A search index handles the management of documents of a specific type in the 
    index, but no queries. 
    The default implementation maps many of the methods, so most subclasses will 
    only have to implement ``update_dict`` and ``remove_dict``. 
    """    
    
    def __init__(self):
        pass
    
    def insert_dict(self, data):
        """ Insert new data from a dictionary. """
        return self.update_dict(data)
        
    def insert_entity(self, entity):
        """ Insert new data from a domain object. """
        return self.insert_dict(entity.as_dict())
    
    def update_dict(self, data):
        """ Update data from a dictionary. """
        log.debug("NOOP Index: %s" % ",".join(data.keys()))
    
    def update_entity(self, entity):
        """ Update data from a domain object. """
        # in convention we trust:
        return self.update_dict(entity.as_dict())
    
    def remove_dict(self, data):
        """ Delete an index entry uniquely identified by ``data``. """
        log.debug("NOOP Delete: %s" % ",".join(data.keys()))
        
    def remove_entity(self, entity):
        """ Delete ``entity``. """
        return self.remove_dict(entity.as_dict())
        
    def clear(self):
        """ Delete the complete index. """
        clear_index()

    def get_all_entity_ids(self):
        """ Return a list of entity IDs in the index. """
        raise NotImplemented
        
class NoopSearchIndex(SearchIndex): pass

class PackageSearchIndex(SearchIndex):
    def remove_dict(self, pkg_dict):
        self.delete_package(pkg_dict)
    
    def update_dict(self, pkg_dict):
        self.index_package(pkg_dict)

    def index_package(self, pkg_dict):
        if pkg_dict is None:  
            return 

        if (not pkg_dict.get('state')) or ('active' not in pkg_dict.get('state')):
            return self.delete_package(pkg_dict)

        conn = make_connection()
        index_fields = RESERVED_FIELDS + pkg_dict.keys()
            
        # include the extras in the main namespace
        extras = pkg_dict.get('extras', {})
        for (key, value) in extras.items():
            if isinstance(value, (tuple, list)):
                value = " ".join(map(unicode, value))
            key = ''.join([c for c in key if c in KEY_CHARS])
            pkg_dict['extras_' + key] = value
            if key not in index_fields:
                pkg_dict[key] = value
        if 'extras' in pkg_dict:
            del pkg_dict['extras']

        # flatten the structure for indexing: 
        for resource in pkg_dict.get('resources', []):
            for (okey, nkey) in [('description', 'res_description'),
                                 ('format', 'res_format'),
                                 ('url', 'res_url')]:
                pkg_dict[nkey] = pkg_dict.get(nkey, []) + [resource.get(okey, u'')]
        if 'resources' in pkg_dict:
            del pkg_dict['resources']
        
        # index relationships as <type>:<object>
        rel_dict = {}
        rel_types = list(itertools.chain(RELATIONSHIP_TYPES))
        for rel in pkg_dict.get('relationships', []):
            _type = rel.get('type', 'rel')
            if (_type in pkg_dict.keys()) or (_type not in rel_types): 
                continue
            rel_dict[_type] = rel_dict.get(_type, []) + [rel.get('object')]
        
        pkg_dict.update(rel_dict)
        
        if 'relationships' in pkg_dict:
            del pkg_dict['relationships']

        pkg_dict[TYPE_FIELD] = PACKAGE_TYPE
        pkg_dict = dict([(k.encode('ascii', 'ignore'), v) for (k, v) in pkg_dict.items()])
        
        # mark this CKAN instance as data source:
        pkg_dict['site_id'] = config.get('ckan.site_id')
        
        # send to solr:  
        try:
            conn.add_many([pkg_dict])
            conn.commit(wait_flush=False, wait_searcher=False)
        except Exception, e:
            log.exception(e)
            raise SearchIndexError(e)
        finally:
            conn.close()  
        
        log.debug("Updated index for %s" % pkg_dict.get('name'))

    def delete_package(self, pkg_dict):
        conn = make_connection()
        query = "+%s:%s +id:\"%s\" +site_id:\"%s\"" % (TYPE_FIELD, PACKAGE_TYPE,
                                                       pkg_dict.get('id'),
                                                       config.get('ckan.site_id'))
        try:
            conn.delete_query(query)
            conn.commit()
        except Exception, e:
            log.exception(e)
            raise SearchIndexError(e)
        finally:
            conn.close()
