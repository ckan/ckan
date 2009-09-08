from sqlalchemy import *
from migrate import *
import uuid

metadata = MetaData(migrate_engine)

def make_uuid():
    return unicode(uuid.uuid4())

group_table = Table('group', metadata,
        Column('id', types.UnicodeText, primary_key=True, default=make_uuid),
        Column('name', types.UnicodeText, unique=True, nullable=False),
        Column('title', types.UnicodeText),
        Column('description', types.UnicodeText),
)

package_group_table = Table('package_groups', metadata,
        Column('id', types.UnicodeText, primary_key=True, default=make_uuid),
        Column('package_id', types.Integer, ForeignKey('package.id')),
        Column('group_id', types.UnicodeText, ForeignKey('group.id'), default=make_uuid),
        )

def upgrade():
    group_table.create()
    package_group_table.create()

def downgrade():
    group_table.drop()
    package_group_table.drop()
