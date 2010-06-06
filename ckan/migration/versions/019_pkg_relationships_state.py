from sqlalchemy import *
from migrate import *
import migrate.changeset

metadata = MetaData(migrate_engine)

package_relationship_table = Table('package_relationship',
                                   metadata, autoload=True)
package_relationship_revision_table = Table('package_relationship_revision',
                                            metadata, autoload=True)

def upgrade():
    state_column = Column('state', UnicodeText)
    state_column.create(package_relationship_table)
    state_column = Column('state', UnicodeText)
    state_column.create(package_relationship_revision_table)
    # No package relationship objects exist to migrate, so no
    # need to populate state column

def downgrade():
    raise NotImplementedError()
    
