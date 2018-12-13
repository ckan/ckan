# encoding: utf-8


def upgrade(migrate_engine):
    migrate_engine.execute('''
        BEGIN;

        ALTER TABLE resource_view
            DROP CONSTRAINT resource_view_resource_id_fkey;

        ALTER TABLE resource_view
            ADD CONSTRAINT resource_view_resource_id_fkey
            FOREIGN KEY (resource_id) REFERENCES resource(id)
            ON UPDATE CASCADE ON DELETE CASCADE;

        COMMIT;
    ''')
