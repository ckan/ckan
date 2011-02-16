from sqlalchemy import *
from migrate import *


def upgrade(migrate_engine):
    meta = MetaData()

    state = Table('state', meta,
      Column('id', Integer() ,  primary_key=True, nullable=False),
      Column('name', Unicode(100)),
    )

    revision = Table('revision', meta,
      Column('id', Integer() ,  primary_key=True, nullable=False),
      Column('timestamp', DateTime(timezone=False)   ),
      Column('author', Unicode(200)),
      Column('message', UnicodeText()),
      Column('state_id', Integer()   ),
    )

    apikey = Table('apikey', meta,
      Column('id', Integer() ,  primary_key=True, nullable=False),
      Column('name', UnicodeText()),
      Column('key', UnicodeText()),
    )

    license = Table('license', meta,
      Column('id', Integer() ,  primary_key=True, nullable=False),
      Column('name', Unicode(100)),
      # Column('state_id', Integer(), ForeignKey('state.id')),
      Column('state_id', Integer())
    )

    package = Table('package', meta,
      Column('id', Integer() ,  primary_key=True, nullable=False),
      Column('name', Unicode(100) ,  nullable=False, unique=True),
      Column('title', UnicodeText()),
      Column('version', Unicode(100)),
      Column('url', UnicodeText()),
      Column('download_url', UnicodeText()),
      Column('notes', UnicodeText()),
      Column('license_id', Integer(), ForeignKey('license.id') ),
      Column('state_id', Integer(), ForeignKey('state.id') ),
      Column('revision_id', Integer(), ForeignKey('revision.id') ),
    )

    package_revision = Table('package_revision', meta,
      Column('id', Integer(), primary_key=True, nullable=False),
      Column('name', Unicode(100), nullable=False),
      Column('title', UnicodeText()),
      Column('version', Unicode(100)),
      Column('url', UnicodeText()),
      Column('download_url', UnicodeText()),
      Column('notes', UnicodeText()),
      Column('license_id', Integer(), ForeignKey('license.id')  ),
      Column('state_id', Integer(), ForeignKey('state.id')   ),
      Column('revision_id', Integer() , ForeignKey('revision.id'), primary_key=True),
      Column('continuity_id', Integer(), ForeignKey('package.id') ),
    )

    tag = Table('tag', meta,
      Column('id', Integer() ,  primary_key=True, nullable=False),
      Column('name', Unicode(100), nullable=False, unique=True),
    )

    package_tag = Table('package_tag', meta,
      Column('id', Integer() ,  primary_key=True, nullable=False),
      Column('package_id', Integer(), ForeignKey('package.id') ),
      Column('tag_id', Integer(), ForeignKey('tag.id') ),
      Column('state_id', Integer(), ForeignKey('state.id') ),
      Column('revision_id', Integer(), ForeignKey('revision.id')  ),
    )

    package_tag_revision = Table('package_tag_revision', meta,
      Column('id', Integer() ,  primary_key=True, nullable=False),
      Column('package_id', Integer(), ForeignKey('package.id') ),
      Column('tag_id', Integer(), ForeignKey('tag.id') ),
      Column('state_id', Integer(), ForeignKey('state.id') ),
      Column('revision_id', Integer() , ForeignKey('revision.id'), primary_key=True),
      Column('continuity_id', Integer(), ForeignKey('package_tag.id') ),
    )

    package_extra = Table('package_extra', meta,
      Column('id', Integer() ,  primary_key=True, nullable=False),
      Column('package_id', Integer(), ForeignKey('package.id') ),
      Column('key', UnicodeText()),
      Column('value', UnicodeText()),
      Column('state_id', Integer(), ForeignKey('state.id') ),
      Column('revision_id', Integer(), ForeignKey('revision.id')  ),
    )

    package_extra_revision = Table('package_extra_revision', meta,
      Column('id', Integer() ,  primary_key=True, nullable=False),
      Column('package_id', Integer(), ForeignKey('package.id') ),
      Column('key', UnicodeText()),
      Column('value', UnicodeText()),
      Column('state_id', Integer(), ForeignKey('state.id') ),
      Column('revision_id', Integer(), ForeignKey('revision.id'), primary_key=True),
      Column('continuity_id', Integer(), ForeignKey('package_extra.id') ),
    )

    meta.bind = migrate_engine
    meta.create_all()

def downgrade(migrate_engine):
    raise NotImplementedError()
