def upgrade(migrate_engine):
    migrate_engine.execute(
        '''
        CREATE INDEX idx_activity_user_id ON activity
        (user_id, timestamp);
        CREATE INDEX idx_activity_object_id ON activity
        (object_id, timestamp);
        CREATE INDEX idx_activity_detail_activity_id ON activity_detail
        (activity_id);
        CREATE INDEX idx_resource_resource_group_id ON resource_revision
        (resource_group_id, current);
        '''
    )
