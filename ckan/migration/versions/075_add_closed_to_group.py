import ckan.model


def upgrade(migrate_engine):
    migrate_engine.execute(
        '''
        ALTER TABLE "group"
            ADD COLUMN "closed" BOOLEAN DEFAULT FALSE;
        UPDATE "group" set closed=false;
        ALTER TABLE "group_revision"
            ADD COLUMN "closed" BOOLEAN DEFAULT FALSE;
        UPDATE "group_revision" set closed=false;
        '''
    )
