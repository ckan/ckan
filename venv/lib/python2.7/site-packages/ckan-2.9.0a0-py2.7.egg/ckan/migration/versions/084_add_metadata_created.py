# encoding: utf-8


def upgrade(migrate_engine):
    migrate_engine.execute('''
        ALTER TABLE package_revision
            ADD COLUMN metadata_created timestamp without time zone;
        ALTER TABLE package
            ADD COLUMN metadata_created timestamp without time zone;

        UPDATE package SET metadata_created=
            (SELECT revision_timestamp
             FROM package_revision
             WHERE id=package.id
             ORDER BY revision_timestamp ASC
             LIMIT 1);
    ''')
