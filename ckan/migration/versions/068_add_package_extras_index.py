# encoding: utf-8


def upgrade(migrate_engine):
    migrate_engine.execute(
        '''
        CREATE INDEX idx_package_extra_package_id ON package_extra_revision
        USING BTREE (package_id, current);
        '''
    )
