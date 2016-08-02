# encoding: utf-8

import ckan.model


def upgrade(migrate_engine):
    migrate_engine.execute(
        '''
        ALTER TABLE "resource"
            ADD COLUMN "package_id" text NOT NULL DEFAULT '';
        UPDATE "resource" AS R
        SET package_id = G.package_id
        FROM "resource_group" AS G
        WHERE R.resource_group_id = G.id;
        ALTER TABLE "resource" DROP COLUMN "resource_group_id";

        ALTER TABLE "resource_revision"
            ADD COLUMN "package_id" text NOT NULL DEFAULT '';
        UPDATE "resource_revision" AS R
        SET package_id = G.package_id
        FROM "resource_group_revision" AS G
        WHERE R.resource_group_id = G.id;
        ALTER TABLE "resource_revision" DROP COLUMN "resource_group_id";

        ALTER TABLE resource_group_revision
            DROP CONSTRAINT resource_group_revision_continuity_id_fkey;

        DROP TABLE "resource_group_revision";
        DROP TABLE "resource_group";
        '''
    )
