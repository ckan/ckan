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

        ALTER TABLE "group"
            ADD COLUMN "closed_date" timestamp without time zone;
        UPDATE "group" set closed_date=NULL;
        ALTER TABLE "group_revision"
            ADD COLUMN "closed_date" timestamp without time zone;
        UPDATE "group_revision" set closed_date=NULL;

        ALTER TABLE "group"
            ADD COLUMN "related_group_id" TEXT;
        UPDATE "group" set related_group_id=NULL;
        ALTER TABLE "group_revision"
            ADD COLUMN "related_group_id" TEXT;
        UPDATE "group_revision" set related_group_id=NULL;

        ALTER TABLE "group"
            ADD COLUMN "related_group_relationship" TEXT;
        UPDATE "group" set related_group_relationship=NULL;
        ALTER TABLE "group_revision"
            ADD COLUMN "related_group_relationship" TEXT;
        UPDATE "group_revision" set related_group_relationship=NULL;
        '''
    )
