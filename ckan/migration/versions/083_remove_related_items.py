
def upgrade(migrate_engine):
    migrate_engine.execute('''
BEGIN;
DROP TABLE related_dataset;
DROP TABLE related;
COMMIT;
    ''')
