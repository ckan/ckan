import socket
import string
import logging
import collections
import json
from dateutil.parser import parse

import re

import solr

from pylons import config
from paste.deploy.converters import asbool

from common import SearchIndexError, make_connection
from ckan.model import PackageRelationship
import ckan.model as model
from ckan.plugins import (PluginImplementations,
                          IPackageController)
import ckan.logic as logic

log = logging.getLogger(__name__)

TYPE_FIELD = "entity_type"
PACKAGE_TYPE = "package"
KEY_CHARS = string.digits + string.letters + "_-"
SOLR_FIELDS = [TYPE_FIELD, "res_url", "text", "urls", "indexed_ts", "site_id"]
RESERVED_FIELDS = SOLR_FIELDS + ["tags", "groups", "res_description",
                                 "res_format", "res_url"]
RELATIONSHIP_TYPES = PackageRelationship.types

# Regular expression used to strip invalid XML characters
_illegal_xml_chars_re = re.compile(u'[\x00-\x08\x0b\x0c\x0e-\x1F\uD800-\uDFFF\uFFFE\uFFFF]')

def escape_xml_illegal_chars(val, replacement=''):
    '''
        Replaces any character not supported by XML with
        a replacement string (default is an empty string)
        Thanks to http://goo.gl/ZziIz
    '''
    return _illegal_xml_chars_re.sub(replacement, val)


def clear_index():
    import solr.core
    conn = make_connection()
    query = "+site_id:\"%s\"" % (config.get('ckan.site_id'))
    try:
        conn.delete_query(query)
        conn.commit()
    except socket.error, e:
        err = 'Could not connect to SOLR %r: %r' % (conn.url, e)
        log.error(err)
        raise SearchIndexError(err)
    except solr.core.SolrException, e:
        err = 'SOLR %r exception: %r' % (conn.url, e)
        log.error(err)
        raise SearchIndexError(err)
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

    def update_dict(self, data):
        """ Update data from a dictionary. """
        log.debug("NOOP Index: %s" % ",".join(data.keys()))

    def remove_dict(self, data):
        """ Delete an index entry uniquely identified by ``data``. """
        log.debug("NOOP Delete: %s" % ",".join(data.keys()))

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

    def update_dict(self, pkg_dict, defer_commit=False):
        self.index_package(pkg_dict, defer_commit)

    def index_package(self, pkg_dict, defer_commit=False):
        if pkg_dict is None:
            return
        pkg_dict['data_dict'] = json.dumps(pkg_dict)

        # add to string field for sorting
        title = pkg_dict.get('title')
        if title:
            pkg_dict['title_string'] = title

        if (not pkg_dict.get('state')) or ('active' not in pkg_dict.get('state')):
            return self.delete_package(pkg_dict)

        index_fields = RESERVED_FIELDS + pkg_dict.keys()

        # include the extras in the main namespace
        extras = pkg_dict.get('extras', [])
        for extra in extras:
            key, value = extra['key'], extra['value']
            if isinstance(value, (tuple, list)):
                value = " ".join(map(unicode, value))
            key = ''.join([c for c in key if c in KEY_CHARS])
            pkg_dict['extras_' + key] = value
            if key not in index_fields:
                pkg_dict[key] = value
        pkg_dict.pop('extras', None)

        # add tags, removing vocab tags from 'tags' list and adding them as
        # vocab_<tag name> so that they can be used in facets
        non_vocab_tag_names = []
        tags = pkg_dict.pop('tags', [])
        context = {'model': model}

        for tag in tags:
            if tag.get('vocabulary_id'):
                data = {'id': tag['vocabulary_id']}
                vocab = logic.get_action('vocabulary_show')(context, data)
                key = u'vocab_%s' % vocab['name']
                if key in pkg_dict:
                    pkg_dict[key].append(tag['name'])
                else:
                    pkg_dict[key] = [tag['name']]
            else:
                non_vocab_tag_names.append(tag['name'])

        pkg_dict['tags'] = non_vocab_tag_names

        # add groups
        groups = pkg_dict.pop('groups', [])

        # we use the capacity to make things private in the search index
        if pkg_dict['private']:
            pkg_dict['capacity'] = 'private'
        else:
            pkg_dict['capacity'] = 'public'

        pkg_dict['groups'] = [group['name'] for group in groups]

        # if there is an owner_org we want to add this to groups for index
        # purposes
        if pkg_dict.get('organization'):
           pkg_dict['organization'] = pkg_dict['organization']['name']
        else:
           pkg_dict['organization'] = None

        # tracking
        tracking_summary = pkg_dict.pop('tracking_summary', None)
        if tracking_summary:
            pkg_dict['views_total'] = tracking_summary['total']
            pkg_dict['views_recent'] = tracking_summary['recent']

        # flatten the structure for indexing:
        for resource in pkg_dict.get('resources', []):
            for (okey, nkey) in [('description', 'res_description'),
                                 ('format', 'res_format'),
                                 ('url', 'res_url')]:
                pkg_dict[nkey] = pkg_dict.get(nkey, []) + [resource.get(okey, u'')]
        pkg_dict.pop('resources', None)

        rel_dict = collections.defaultdict(list)
        subjects = pkg_dict.pop("relationships_as_subject", [])
        objects = pkg_dict.pop("relationships_as_object", [])
        for rel in objects:
            type = model.PackageRelationship.forward_to_reverse_type(rel['type'])
            rel_dict[type].append(model.Package.get(rel['subject_package_id']).name)
        for rel in subjects:
            type = rel['type']
            rel_dict[type].append(model.Package.get(rel['object_package_id']).name)
        for key, value in rel_dict.iteritems():
            if key not in pkg_dict:
                pkg_dict[key] = value

        pkg_dict[TYPE_FIELD] = PACKAGE_TYPE

        # Save dataset type
        pkg_dict['dataset_type'] = pkg_dict['type']

        # clean the dict fixing keys and dates
        # FIXME where are we getting these dirty keys from?  can we not just
        # fix them in the correct place or is this something that always will
        # be needed?  For my data not changing the keys seems to not cause a
        # problem.
        new_dict = {}
        for key, value in pkg_dict.items():
            key = key.encode('ascii', 'ignore')
            if key.endswith('_date'):
                try:
                    value = parse(value).isoformat() + 'Z'
                except ValueError:
                    continue
            new_dict[key] = value
        pkg_dict = new_dict

        for k in ('title', 'notes', 'title_string'):
            if k in pkg_dict and pkg_dict[k]:
                pkg_dict[k] = escape_xml_illegal_chars(pkg_dict[k])

        # modify dates (SOLR is quite picky with dates, and only accepts ISO dates
        # with UTC time (i.e trailing Z)
        # See http://lucene.apache.org/solr/api/org/apache/solr/schema/DateField.html
        pkg_dict['metadata_created'] += 'Z'
        pkg_dict['metadata_modified'] += 'Z'

        # mark this CKAN instance as data source:
        pkg_dict['site_id'] = config.get('ckan.site_id')

        # Strip a selection of the fields.
        # These fields are possible candidates for sorting search results on,
        # so we strip leading spaces because solr will sort " " before "a" or "A".
        for field_name in ['title']:
            try:
                value = pkg_dict.get(field_name)
                if value:
                    pkg_dict[field_name] = value.lstrip()
            except KeyError:
                pass

        # add a unique index_id to avoid conflicts
        import hashlib
        pkg_dict['index_id'] = hashlib.md5('%s%s' % (pkg_dict['id'],config.get('ckan.site_id'))).hexdigest()

        for item in PluginImplementations(IPackageController):
            pkg_dict = item.before_index(pkg_dict)

        assert pkg_dict, 'Plugin must return non empty package dict on index'

        # send to solr:
        try:
            conn = make_connection()
            commit = not defer_commit
            if not asbool(config.get('ckan.search.solr_commit', 'true')):
                commit = False
            conn.add_many([pkg_dict], _commit=commit)
        except solr.core.SolrException, e:
            msg = 'Solr returned an error: {0} {1} - {2}'.format(
                e.httpcode, e.reason, e.body[:1000] # limit huge responses
            )
            raise SearchIndexError(msg)
        except socket.error, e:
            err = 'Could not connect to Solr using {0}: {1}'.format(conn.url, str(e))
            log.error(err)
            raise SearchIndexError(err)
        finally:
            conn.close()

        commit_debug_msg = 'Not commited yet' if defer_commit else 'Commited'
        log.debug('Updated index for %s [%s]' % (pkg_dict.get('name'), commit_debug_msg))

    def commit(self):
        try:
            conn = make_connection()
            conn.commit(wait_searcher=False)
        except Exception, e:
            log.exception(e)
            raise SearchIndexError(e)
        finally:
            conn.close()


    def delete_package(self, pkg_dict):
        conn = make_connection()
        query = "+%s:%s (+id:\"%s\" OR +name:\"%s\") +site_id:\"%s\"" % (TYPE_FIELD, PACKAGE_TYPE,
                                                       pkg_dict.get('id'), pkg_dict.get('id'),
                                                       config.get('ckan.site_id'))
        try:
            conn.delete_query(query)
            if asbool(config.get('ckan.search.solr_commit', 'true')):
                conn.commit()
        except Exception, e:
            log.exception(e)
            raise SearchIndexError(e)
        finally:
            conn.close()
