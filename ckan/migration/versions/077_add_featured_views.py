def upgrade(migrate_engine):
    migrate_engine.execute(
        '''
        BEGIN;
        ALTER TABLE "resource_view" ADD COLUMN "featured" boolean DEFAULT FALSE;
        COMMIT;
        '''
    )
