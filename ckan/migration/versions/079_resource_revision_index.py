# encoding: utf-8


def upgrade(migrate_engine):
    migrate_engine.execute(
        '''
        CREATE INDEX idx_resource_continuity_id
            ON resource_revision (continuity_id);
        '''
    )
