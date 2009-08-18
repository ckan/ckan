from sqlalchemy import *
from migrate import *

meta = MetaData(migrate_engine)

package_tag = Table('package_tag', meta,
  Column('id', Integer() ,  primary_key=True, nullable=False),
  Column('package_id', Integer()   ),
  Column('tag_id', Integer()   ),
  Column('state_id', Integer()   ),
  Column('revision_id', Integer()   ),
)

apikey = Table('apikey', meta,
  Column('id', Integer() ,  primary_key=True, nullable=False),
  Column('name', UnicodeText()),
  Column('key', UnicodeText()),
)

license = Table('license', meta,
  Column('id', Integer() ,  primary_key=True, nullable=False),
  Column('name', Unicode(100)),
  Column('state_id', Integer()   ),
)

package = Table('package', meta,
  Column('id', Integer() ,  primary_key=True, nullable=False),
  Column('name', Unicode(100) ,  nullable=False),
  Column('title', UnicodeText()),
  Column('version', Unicode(100)),
  Column('url', UnicodeText()),
  Column('download_url', UnicodeText()),
  Column('notes', UnicodeText()),
  Column('license_id', Integer()   ),
  Column('state_id', Integer()   ),
  Column('revision_id', Integer()   ),
)

package_extra_revision = Table('package_extra_revision', meta,
  Column('id', Integer() ,  primary_key=True, nullable=False),
  Column('package_id', Integer()   ),
  Column('key', UnicodeText()),
  Column('value', UnicodeText()),
  Column('state_id', Integer()   ),
  Column('revision_id', Integer() ,  primary_key=True),
  Column('continuity_id', Integer()   ),
)

package_revision = Table('package_revision', meta,
  Column('id', Integer() ,  primary_key=True, nullable=False),
  Column('name', String(length=None, convert_unicode=False, assert_unicode=None) ,  nullable=False),
  Column('title', UnicodeText()),
  Column('version', Unicode(100)),
  Column('url', UnicodeText()),
  Column('download_url', UnicodeText()),
  Column('notes', UnicodeText()),
  Column('license_id', Integer()   ),
  Column('state_id', Integer()   ),
  Column('revision_id', Integer() ,  primary_key=True),
  Column('continuity_id', Integer()   ),
)

state = Table('state', meta,
  Column('id', Integer() ,  primary_key=True, nullable=False),
  Column('name', Unicode(100)),
)

tag = Table('tag', meta,
  Column('id', Integer() ,  primary_key=True, nullable=False),
  Column('name', String(length=None, convert_unicode=False, assert_unicode=None) ,  nullable=False),
)

package_extra = Table('package_extra', meta,
  Column('id', Integer() ,  primary_key=True, nullable=False),
  Column('package_id', Integer()   ),
  Column('key', UnicodeText()),
  Column('value', UnicodeText()),
  Column('state_id', Integer()   ),
  Column('revision_id', Integer()   ),
)

package_tag_revision = Table('package_tag_revision', meta,
  Column('id', Integer() ,  primary_key=True, nullable=False),
  Column('package_id', Integer()   ),
  Column('tag_id', Integer()   ),
  Column('state_id', Integer()   ),
  Column('revision_id', Integer() ,  primary_key=True),
  Column('continuity_id', Integer()   ),
)

revision = Table('revision', meta,
  Column('id', Integer() ,  primary_key=True, nullable=False),
  Column('timestamp', DateTime(timezone=False)   ),
  Column('author', Unicode(200)),
  Column('message', UnicodeText()),
  Column('state_id', Integer()   ),
)



def upgrade():
    meta.create_all()

def downgrade():
    raise NotImplementedError()
