from sqlalchemy import *
from migrate import *
import uuid

metadata = MetaData(migrate_engine)

def make_uuid():
    return unicode(uuid.uuid4())

# you need to load this for foreign keys to work in package_group_table
package_table = Table('package', metadata, autoload=True)

group_table = Table('group', metadata,
        Column('id', UnicodeText, primary_key=True, default=make_uuid),
        Column('name', UnicodeText, unique=True, nullable=False),
        Column('title', UnicodeText),
        Column('description', UnicodeText),
)

package_group_table = Table('package_group', metadata,
        Column('id', UnicodeText, primary_key=True, default=make_uuid),
        Column('package_id', Integer, ForeignKey('package.id')),
        Column('group_id', UnicodeText, ForeignKey('group.id')),
        )

def upgrade():
    group_table.create()
    package_group_table.create()

def downgrade():
    raise NotImplementedError()

