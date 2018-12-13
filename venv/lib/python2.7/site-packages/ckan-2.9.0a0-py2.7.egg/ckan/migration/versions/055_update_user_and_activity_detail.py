# encoding: utf-8

def upgrade(migrate_engine):
    migrate_engine.execute('''
        ALTER TABLE activity_detail
            ALTER COLUMN activity_id DROP NOT NULL;

        ALTER TABLE "user"
            ALTER COLUMN name SET NOT NULL;
    '''
    )
