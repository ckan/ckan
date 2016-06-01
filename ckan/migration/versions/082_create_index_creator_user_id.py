# encoding: utf-8


def upgrade(migrate_engine):
    migrate_engine.execute(
        '''
        CREATE INDEX idx_package_creator_user_id ON package
        USING BTREE (creator_user_id);
        '''
    )
