# encoding: utf-8

import vdm.sqlalchemy


def upgrade(migrate_engine):
    migrate_engine.execute(
        '''
        ALTER TABLE "system_info"
            ADD COLUMN "state" text NOT NULL DEFAULT '{state}';

        ALTER TABLE "system_info_revision"
            ADD COLUMN "state" text NOT NULL DEFAULT '{state}';

        ALTER TABLE system_info_revision
            ADD COLUMN expired_id text,
            ADD COLUMN revision_timestamp timestamp without time zone,
            ADD COLUMN expired_timestamp timestamp without time zone,
            ADD COLUMN current boolean;

        ALTER TABLE system_info_revision
            DROP CONSTRAINT "system_info_revision_key_key";

        '''.format(state=vdm.sqlalchemy.State.ACTIVE)
    )
