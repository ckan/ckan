from datetime import datetime

from sqlalchemy import *
from migrate import *
import migrate.changeset


domain_obj_names = ['rating', 'group', 'user']

def upgrade(migrate_engine):
    metadata = MetaData()
    metadata.bind = migrate_engine
    # Use sql instead of migrate.changeset because user and group are sql
    # reserved words and migrate doesn't quote them.
    for domain_obj_name in domain_obj_names:
        sql = 'ALTER TABLE "%s" ADD created TIMESTAMP WITHOUT TIME ZONE' % domain_obj_name
        migrate_engine.execute(sql)

    now = datetime.now()
    for domain_obj_name in domain_obj_names[::-1]:
        table = Table(domain_obj_name, metadata, autoload=True)
        migrate_engine.execute(table.update(values={table.c.created:now}))

def downgrade(migrate_engine):
    raise NotImplementedError()
