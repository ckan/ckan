# encoding: utf-8


def upgrade(migrate_engine):
    migrate_engine.execute(
        '''
        BEGIN;

        UPDATE resource_view
        SET view_type = 'text_view' WHERE view_type = 'text';

        UPDATE resource_view
        SET view_type = 'pdf_view' WHERE view_type = 'pdf';

        COMMIT;
        '''
    )
