from sqlalchemy import *
from migrate import *
import datetime
import uuid
from migrate.changeset.constraint import PrimaryKeyConstraint

metadata = MetaData(migrate_engine)

def make_uuid():
    return unicode(uuid.uuid4())

harvest_source_table = Table('harvest_source', metadata,
        Column('id', UnicodeText, primary_key=True, default=make_uuid),
        Column('status', UnicodeText, default=u'New'),
        Column('url', UnicodeText, unique=True, nullable=False),
        Column('description', UnicodeText, default=u''),                      
        Column('user_ref', UnicodeText, default=u''),
        Column('publisher_ref', UnicodeText, default=u''),
        Column('created', DateTime, default=datetime.datetime.utcnow),
)

harvesting_job_table = Table('harvesting_job', metadata,
        Column('id', UnicodeText, primary_key=True, default=make_uuid),
        Column('status', UnicodeText, default=u''),
        Column('created', DateTime, default=datetime.datetime.utcnow),
        Column('user_ref', UnicodeText, nullable=False),
        Column('report', UnicodeText, default=u''),                     
        Column('source_id', UnicodeText, ForeignKey('harvest_source.id')), 
)

def upgrade():
    harvest_source_table.create()
    harvesting_job_table.create()

def downgrade():
    harvesting_job_table.drop()
    harvest_source_table.drop()

