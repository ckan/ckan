# encoding: utf-8


def upgrade(migrate_engine):
    migrate_engine.execute(
        '''
        BEGIN;

        UPDATE resource_view
        SET view_type = 'image_view' WHERE view_type = 'image';

        UPDATE resource_view
        SET view_type = 'webpage_view' WHERE view_type = 'webpage';

        COMMIT;
        '''
    )
