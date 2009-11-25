from sqlalchemy import *
from migrate import *
import migrate.changeset

metadata = MetaData(migrate_engine)

package_table = Table('package', metadata, autoload=True)
package_search_table = Table('package_search', metadata,
        Column('package_id', Integer, ForeignKey('package.id'), primary_key=True),
        )

def upgrade():
    package_search_table.create()
    sql = 'ALTER TABLE package_search ADD COLUMN search_vector tsvector'
    migrate_engine.execute(sql)

    print 'IMPORTANT! Now run:\n  paster create-search-index'

def downgrade():
    raise NotImplementedError()
