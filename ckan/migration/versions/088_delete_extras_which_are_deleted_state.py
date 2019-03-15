# encoding: utf-8


def upgrade(migrate_engine):
    migrate_engine.execute(
        '''
            ALTER TABLE "package_extra_revision"
              DROP CONSTRAINT package_extra_revision_continuity_id_fkey;
            ALTER TABLE "group_extra_revision"
              DROP CONSTRAINT group_extra_revision_continuity_id_fkey;
            DELETE FROM "package_extra" WHERE state='deleted';
            DELETE FROM "group_extra" WHERE state='deleted';
        '''
    )
