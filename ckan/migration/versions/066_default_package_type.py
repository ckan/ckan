# encoding: utf-8


def upgrade(migrate_engine):

    update_statement = '''
BEGIN;

UPDATE package SET type = 'dataset' WHERE type IS NULL;

COMMIT;

'''
    migrate_engine.execute(update_statement)
