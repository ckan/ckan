import itertools
import string
from solr import SolrConnection # == solrpy
import logging
log = logging.getLogger(__name__)

TYPE_FIELD = "entity_type"
PACKAGE_TYPE = "package"
KEY_CHARS = string.digits + string.letters + "_-"

SOLR_FIELDS = [TYPE_FIELD, "res_url", "text", "urls", "indexed_ts", "site_id"]

RESERVED_FIELDS = SOLR_FIELDS + ["tags", "groups", "res_description", 
                                 "res_format", "res_url"]
                                 
# HACK: this is copied over from model.PackageRelationship 
RELATIONSHIP_TYPES = [(u'depends_on', u'dependency_of'),
                      (u'derives_from', u'has_derivation'),
                      (u'links_to', u'linked_from'),
                      (u'child_of', u'parent_of'),
                     ]
                     
def make_connection(config):
    url = config.get('solr_url', 'http://localhost:8983/solr')
    user = config.get('solr_user')
    password = config.get('solr_password')

    if user is not None and password is not None:
        return SolrConnection(url, http_user=user, http_pass=password)
    else:
        return SolrConnection(url)


def index_package(pkg_dict, config):
    if pkg_dict is None:  
        return 
    if (not pkg_dict.get('state')) or ('active' not in pkg_dict.get('state')):
        return delete_package(pkg_dict, config)
    conn = make_connection(config)
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
    finally:
        conn.close()  
    
    log.debug("Updated index for %s" % pkg_dict.get('name'))


def delete_package(pkg_dict, config):
    conn = make_connection(config)
    query = "+%s:%s +id:\"%s\" +site_id:\"%s\"" % (TYPE_FIELD, PACKAGE_TYPE,
                                                   pkg_dict.get('id'),
                                                   config.get('ckan.site_id'))
    try:
        conn.delete_query(query)
        conn.commit()
    finally:
        conn.close()

    
def clear_index(config):
    conn = make_connection(config)
    query = "+site_id:\"%s\"" % (config.get('ckan.site_id'))
    try:
        conn.delete_query(query)
        conn.commit()
    finally:
        conn.close()
    
