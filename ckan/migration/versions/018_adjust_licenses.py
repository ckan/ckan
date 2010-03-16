from sqlalchemy import *
from migrate import *
import uuid

metadata = MetaData(migrate_engine)

def make_uuid():
    return unicode(uuid.uuid4())

#license_table = Table('license', metadata, autoload=True)
#license_table = Table('license', metadata,
#        Column('id', Integer, primary_key=True),
#        Column('name', Unicode(100)),
#        )
#
#package_table = Table('package', metadata, autoload=True)
#package_table = Table('package', metadata,
#        Column('id', UnicodeText, primary_key=True, default=make_uuid),
#        Column('name', Unicode(100), unique=True, nullable=False),
#        Column('title', UnicodeText),
#        Column('version', Unicode(100)),
#        Column('url', UnicodeText),
#        Column('author', UnicodeText),
#        Column('author_email', UnicodeText),
#        Column('maintainer', UnicodeText),
#        Column('maintainer_email', UnicodeText),                      
#        Column('notes', UnicodeText),
#        Column('license_id', Integer, ForeignKey('license.id')),
#)

def upgrade():
    print "Changing package license_ids to strings."
#    license_table.drop()
#    package_license_col = package_table.c.license_id
#    package_license_col.drop()
#    package_license_col = Column('license_id', String(100), nullable=True)
#    package_license_col.create(package_table)
    drop_fk_constraint = "ALTER TABLE package DROP CONSTRAINT package_license_id_fkey;"
    change_license_id_type_on_package_table = "ALTER TABLE package ALTER COLUMN license_id TYPE character varying(100);"
    change_license_id_type_on_package_revision_table = "ALTER TABLE package ALTER COLUMN license_id TYPE character varying(100);"
    drop_licenses_table = "DROP TABLE license CASCADE;"
    
    migrate_engine.execute(drop_fk_constraint)
    migrate_engine.execute(change_license_id_type_on_package_table)
    migrate_engine.execute(change_license_id_type_on_package_revision_table)
    migrate_engine.execute(drop_licenses_table)

def downgrade():
    raise NotImplementedError()

