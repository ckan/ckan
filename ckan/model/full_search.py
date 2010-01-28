import re

import sqlalchemy

from meta import *


class SearchVectorTrigger(sqlalchemy.orm.interfaces.MapperExtension):
    match_bad_chars = re.compile('[%"\'\\\r\n#><]')
    
    def after_insert(self, mapper, connection, instance):
        self.update_vector(instance, connection)

    def after_update(self, mapper, connection, instance):
        self.update_vector(instance, connection)

    def update_vector(self, instance, engine):
        if instance.__class__.__name__ == 'Package':
            pkgs = [instance]
        elif instance.__class__.__name__ == 'PackageTag':
            if instance.package:
                pkgs = [instance.package]
            else:
                pkgs = []
        elif instance.__class__.__name__ == 'Group':
            pkgs = instance.packages

        for pkg in pkgs:
            pkg_dict = pkg.as_dict() # note: license and extras aren't
                                     # updated here yet for new items?
            self.update_package_vector(pkg_dict, engine)

    def update_package_vector(self, pkg_dict, engine):
        if isinstance(pkg_dict['tags'], (list, tuple)):
            pkg_dict['tags'] = ' '.join(pkg_dict['tags'])
        if isinstance(pkg_dict['groups'], (list, tuple)):
            pkg_dict['groups'] = ' '.join(pkg_dict['groups'])

        document_a = ' '.join((pkg_dict['name'] or '', pkg_dict['title'] or ''))
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
        document_b = ' '.join(document_b_items)

        def make_document_safe(document):
            doc = self.match_bad_chars.sub(' ', document)
            doc = doc.encode('ascii', 'ignore')
            doc = doc.replace('\\', '')
            return doc
        document_a = make_document_safe(document_a)
        document_b = make_document_safe(document_b)
        # Create weighted vector
        vector = 'setweight(to_tsvector(\'%s\'), \'A\') || setweight(to_tsvector(\'%s\'), \'D\')' % (document_a, document_b)
        # See if record for this pkg exists, otherwise create it
        sql = "SELECT package_id FROM package_search WHERE package_id = '%s'" % pkg_dict['id']
        res = engine.execute(sql)
        pkgs = res.fetchall()
        if not pkgs:
            sql = "INSERT INTO package_search VALUES ('%s', %s)" % (pkg_dict['id'], vector)
        else:
            sql = "UPDATE package_search SET search_vector=%s WHERE package_id='%s'" % (vector, pkg_dict['id'])
        res = engine.execute(sql)
        # uncomment this to print lexemes
        # sql = "SELECT package_id, search_vector FROM package_search WHERE package_id = '%s" % pkg_dict['id']
        # res = engine.execute(sql)
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
