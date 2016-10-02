# encoding: utf-8

WARNING = """

WARNING: The 'related' tables were not deleted as they currently contain data.
Once you have archived the existing data or migrated the data to
ckanext-showcase, you can safely delete the 'related' and 'related_dataset'
tables using:

    psql ckan_default -c 'BEGIN; DROP TABLE related_dataset; \\
    DROP TABLE related; COMMIT;'

"""


def upgrade(migrate_engine):
    existing = migrate_engine.execute("SELECT COUNT(*) FROM related;")\
        .fetchone()
    if existing[0] > 0:
        print WARNING
        return

    migrate_engine.execute('''
BEGIN;
DROP TABLE related_dataset;
DROP TABLE related;
COMMIT;
    ''')
