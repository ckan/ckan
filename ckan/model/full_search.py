from meta import *

import sqlalchemy

class SearchVectorTrigger(sqlalchemy.orm.interfaces.MapperExtension):
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
            tags = pkg.tags
            groups = pkg.groups        
            tag_names = ' '.join([tag.name for tag in tags])
            group_names = ' '.join([group.name for group in groups])
            document_a = ' '.join((pkg.name or '', pkg.title or ''))
            document_b = ' '.join((pkg.notes or '', tag_names or '', group_names or ''))
            def make_document_safe(document):
                return document.replace('\'', '').replace('"', '')
            document_a = make_document_safe(document_a)
            document_b = make_document_safe(document_b)
            # Create weighted vector
            vector = 'setweight(to_tsvector(\'%s\'), \'A\') || setweight(to_tsvector(\'%s\'), \'D\')' % (document_a, document_b)
            # See if record for this pkg exists, otherwise create it
            sql = 'SELECT package_id FROM package_search WHERE package_id = %i' % pkg.id
            res = engine.execute(sql)
            pkgs = res.fetchall()
            if not pkgs:
                sql = 'INSERT INTO package_search VALUES (%i, %s)' % (pkg.id, vector)
            else:
                sql = 'UPDATE package_search SET search_vector=%s WHERE package_id=%i' % (vector, pkg.id)
            res = engine.execute(sql)
            # uncomment this to print lexemes
##            sql = 'SELECT package_id, search_vector FROM package_search WHERE package_id = %i' % pkg.id
##            res = engine.execute(sql)
##            print res.fetchall()

    

def setup_db(event, schema_item, engine):
    sql = 'ALTER TABLE package_search ADD COLUMN search_vector tsvector'
    engine.execute(sql)

package_search_table = Table('package_search', metadata,
        Column('package_id', types.Integer, ForeignKey('package.id'), primary_key=True),
        )

class PackageSearch(object):
    pass
# We need this mapper so that Package can delete orphaned package_search rows
mapper(PackageSearch, package_search_table, properties={})

package_search_table.append_ddl_listener('after-create', setup_db)
