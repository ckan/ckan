from sqlalchemy import *
from migrate import *
import migrate.changeset

metadata = MetaData(migrate_engine)

def upgrade():
    # Upgrade operations go here. Don't create your own engine; use the engine
    # named 'migrate_engine' imported from migrate.
    package = Table('package', metadata, autoload=True)
    package_revision = Table('package_revision', metadata, autoload=True)

    columns = [Column('author', UnicodeText),
               Column('author_email', UnicodeText),
               Column('maintainer', UnicodeText),
               Column('maintainer_email', UnicodeText),
               ]
    columns2 = [Column('author', UnicodeText),
               Column('author_email', UnicodeText),
               Column('maintainer', UnicodeText),
               Column('maintainer_email', UnicodeText),
               ]

    for col in columns:
        col.create(package)
    for col in columns2:
        col.create(package_revision)

def downgrade():
    raise NotImplementedError()
