# encoding: utf-8

def upgrade(migrate_engine):
    migrate_engine.execute('''
        ALTER TABLE resource
            ADD COLUMN created timestamp without time zone;

        ALTER TABLE resource_revision
            ADD COLUMN created timestamp without time zone;
    '''
    )
