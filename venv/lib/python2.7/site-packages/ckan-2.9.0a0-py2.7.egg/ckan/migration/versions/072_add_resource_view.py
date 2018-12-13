# encoding: utf-8


def upgrade(migrate_engine):
    migrate_engine.execute('''
        BEGIN;

        CREATE TABLE resource_view (
            id text NOT NULL,
            resource_id text,
            title text,
            description text,
            view_type text NOT NULL,
            "order" integer NOT NULL,
            config text
        );

        ALTER TABLE resource_view
            ADD CONSTRAINT resource_view_pkey PRIMARY KEY (id);

        ALTER TABLE resource_view
            ADD CONSTRAINT resource_view_resource_id_fkey
            FOREIGN KEY (resource_id) REFERENCES resource(id);

        COMMIT;
    ''')
