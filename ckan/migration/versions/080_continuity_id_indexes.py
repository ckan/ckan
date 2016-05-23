# encoding: utf-8


def upgrade(migrate_engine):
    migrate_engine.execute(
        '''
        CREATE INDEX idx_member_continuity_id
            ON member_revision (continuity_id);
        CREATE INDEX idx_package_tag_continuity_id
            ON package_tag_revision (continuity_id);
        CREATE INDEX idx_package_continuity_id
            ON package_revision (continuity_id);
        CREATE INDEX idx_package_extra_continuity_id
            ON package_extra_revision (continuity_id);
        '''
    )
