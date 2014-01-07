import warnings

from sqlalchemy import exc as sa_exc
from sqlalchemy import *
from migrate import *
import migrate.changeset

def upgrade(migrate_engine):
    # ignore reflection warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=sa_exc.SAWarning)
        metadata = MetaData()
        metadata.bind = migrate_engine

        harvest_source_table = Table('harvest_source', metadata, autoload=True)
        package_table = Table('package', metadata, autoload=True)

        harvested_document_table = Table('harvested_document', metadata,
            Column('url', UnicodeText, nullable=False),
            Column('guid', UnicodeText, default=u''),
            Column('source_id', UnicodeText, ForeignKey('harvest_source.id')),
            Column('package_id', UnicodeText, ForeignKey('package.id')),
        )

        harvested_document_table.c.url.drop()
        harvested_document_table.c.guid.create(harvested_document_table)
        harvested_document_table.c.source_id.create(harvested_document_table)
        harvested_document_table.c.package_id.create(harvested_document_table)

def downgrade(migrate_engine):
    raise NotImplementedError()

