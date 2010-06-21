import re

import sqlalchemy

import meta
from meta import Table, Column, UnicodeText, ForeignKey, mapper, metadata
from notifier import DomainObjectNotification, Notification
from async_notifier import AsyncConsumer, EXCHANGE

__all__ = ['SearchIndexManager', 'SearchIndexer', 'package_search_table']

class SearchIndexManager(AsyncConsumer):
    '''Waits for async notifications about package updates and sends them to
    SearchIndexer.
    In tests, this class is instantiated and then run().
    In deployment, this file is opened in its own process/shell.
    '''
    def __init__ (self):
        queue_name = 'search_indexer'
        routing_key = '*'
        super(SearchIndexManager, self).__init__(queue_name, routing_key)

        self.indexer = SearchIndexer()

    def callback(notification):
        print "MESSAGE"
        if isinstance(notification, DomainObjectNotification):
            self.indexer.update_vector(notification)

if __name__ == "__main__":
    indexer = SearchIndexManager()
    indexer.run()


class SearchIndexer(object):
    def update_vector(self, notification):
        pkg_dicts = []
        if isinstance(notification, DomainObjectNotification):
            obj_dict = notification['payload']
            if notification.domain_object_class == 'Package':
                pkg_dicts = [obj_dict]
            elif notification.domain_object_class == 'PackageTag':
                if instance.package:
                    pkg_dicts = obj_dict['package']
                else:
                    pkg_dicts = []
            elif notification.domain_object_class == 'Group':
                pkg_dicts = obj_dict['packages']

        for pkg_dict in pkg_dicts:
            try:
                # note: license and extras aren't
                # updated here yet for new items?
                self.update_package_vector(pkg_dict)
            except:
                raise

    def update_package_vector(self, pkg_dict):
        engine = meta.Session
        if isinstance(pkg_dict['tags'], (list, tuple)):
            pkg_dict['tags'] = ' '.join(pkg_dict['tags'])
        if isinstance(pkg_dict['groups'], (list, tuple)):
            pkg_dict['groups'] = ' '.join(pkg_dict['groups'])

        document_a = u' '.join((pkg_dict['name'] or u'', pkg_dict['title'] or u''))
        document_b_items = []
        for field_name in ['notes', 'tags', 'groups', 'author', 'maintainer']:
            val = pkg_dict.get(field_name)
            if val:
                document_b_items.append(val)
        extras = pkg_dict['extras']
        for extra_field_name in ['update_frequency', 'geographic_granularity', 'geographic_coverage', 'temporal_granularity', 'temporal_coverage', 'national_statistic', 'categories', 'precision', 'department', 'agency', 'external_reference']:
            val = extras.get(extra_field_name)
            if val:
                document_b_items.append(val)
        document_b = u' '.join(document_b_items)

        # Create weighted vector
        vector_sql = 'setweight(to_tsvector(%s), \'A\') || setweight(to_tsvector(%s), \'D\')'
        params = [document_a.encode('utf8'), document_b.encode('utf8')]
        # See if record for this pkg exists, otherwise create it
        sql = "SELECT package_id FROM package_search WHERE package_id = %s"
        res = engine.execute(sql, pkg_dict['id'])
        pkgs = res.fetchall()
        if not pkgs:
            sql = "INSERT INTO package_search VALUES (%%s, %s)" % vector_sql
            params = [pkg_dict['id']] + params
        else:
            sql = "UPDATE package_search SET search_vector=%s WHERE package_id=%%s" % vector_sql
            params.append(pkg_dict['id'])
        print "SQL", sql, "PARAMS", params
        res = engine.execute(sql, params)
        # uncomment this to print lexemes
        # sql = "SELECT package_id, search_vector FROM package_search WHERE package_id = %s"
        # res = engine.execute(sql, pkg_dict['id'])
        # print res.fetchall()


def setup_db(event, schema_item, engine):
    sql = 'ALTER TABLE package_search ADD COLUMN search_vector tsvector'
    engine.execute(sql)

package_search_table = Table('package_search', metadata,
        Column('package_id', UnicodeText, ForeignKey('package.id'), primary_key=True),
        )

class PackageSearch(object):
    pass
# We need this mapper so that Package can delete orphaned package_search rows
mapper(PackageSearch, package_search_table, properties={})

package_search_table.append_ddl_listener('after-create', setup_db)
