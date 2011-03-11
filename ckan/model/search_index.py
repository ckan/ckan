import sqlalchemy

from meta import Table, Column, UnicodeText, ForeignKey, mapper, metadata

__all__ = ['package_search_table', 'PackageSearch']

def setup_db(event, schema_item, engine):
    sql = 'ALTER TABLE package_search ADD COLUMN search_vector tsvector'
    res = engine.execute(sql)
    res.close()

package_search_table = Table('package_search', metadata,
        Column('package_id', UnicodeText, ForeignKey('package.id'), primary_key=True),
        )

class PackageSearch(object):
    pass
# We need this mapper so that Package can delete orphaned package_search rows
mapper(PackageSearch, package_search_table, properties={})

package_search_table.append_ddl_listener('after-create', setup_db)


