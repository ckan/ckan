/*
This script configures the permissions for the datastore.

It ensures that the datastore read-only user will only be able to select from
the datastore database but has no create/write/edit permission or any
permissions on other databases. You must execute this script as a database
superuser on the PostgreSQL server that hosts your datastore database.

For example, if PostgreSQL is running locally and the "postgres" user has the
appropriate permissions (as in the default Ubuntu PostgreSQL install), you can
run:

    ckan -c /etc/ckan/default/ckan.ini datastore set-permissions | sudo -u postgres psql

Or, if your PostgreSQL server is remote, you can pipe the permissions script
over SSH:

    ckan -c /etc/ckan/default/ckan.ini datastore set-permissions | ssh dbserver sudo -u postgres psql

*/

-- Most of the following commands apply to an explicit database or to the whole
-- 'public' schema, and could be executed anywhere. But ALTER DEFAULT
-- PERMISSIONS applies to the current database, and so we must be connected to
-- the datastore DB:
\connect {datastoredb}

-- Migrate columns using the legacy nested composite type to native JSON.
DO $body$
    DECLARE
        nested_type oid := to_regtype('public.nested');
        column_record record;
        view_info record;
    BEGIN
        IF nested_type IS NULL THEN
            RETURN;
        END IF;

        CREATE TEMP TABLE nested_type_views (
            view_name name PRIMARY KEY,
            definition text NOT NULL,
            owner_name name NOT NULL
        );

        INSERT INTO nested_type_views
        SELECT DISTINCT
            view_class.relname,
            pg_get_viewdef(view_class.oid, true),
            pg_get_userbyid(view_class.relowner)
        FROM pg_depend AS dependency
        JOIN pg_rewrite AS rewrite_rule
            ON rewrite_rule.oid = dependency.objid
        JOIN pg_class AS view_class
            ON view_class.oid = rewrite_rule.ev_class
        JOIN pg_namespace AS view_schema
            ON view_schema.oid = view_class.relnamespace
        JOIN pg_class AS table_class
            ON table_class.oid = dependency.refobjid
        JOIN pg_namespace AS table_schema
            ON table_schema.oid = table_class.relnamespace
        JOIN pg_attribute AS column_info
            ON column_info.attrelid = table_class.oid
            AND column_info.attnum = dependency.refobjsubid
        WHERE dependency.classid = 'pg_rewrite'::regclass
            AND view_class.relkind = 'v'::"char"
            AND view_schema.nspname = 'public'
            AND table_schema.nspname = 'public'
            AND table_class.relkind = 'r'::"char"
            AND column_info.attnum > 0
            AND NOT column_info.attisdropped
            AND column_info.atttypid = nested_type;

        FOR column_record IN
            SELECT view_name
            FROM nested_type_views
        LOOP
            EXECUTE format('DROP VIEW public.%I', column_record.view_name);
        END LOOP;

        FOR column_record IN
            SELECT
                c.relname AS table_name,
                a.attname AS column_name
            FROM pg_attribute AS a
            JOIN pg_class AS c ON c.oid = a.attrelid
            JOIN pg_namespace AS n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public'
                AND c.relkind = 'r'::"char"
                AND a.attnum > 0
                AND NOT a.attisdropped
                AND a.atttypid = nested_type
        LOOP
            EXECUTE format(
                'ALTER TABLE public.%I ALTER COLUMN %I TYPE json ' ||
                'USING (%I).json::json',
                column_record.table_name,
                column_record.column_name,
                column_record.column_name
            );
        END LOOP;

        DROP TYPE public.nested;

        FOR view_info IN
            SELECT view_name, definition, owner_name FROM nested_type_views
        LOOP
            EXECUTE format(
                'CREATE VIEW public.%I AS %s',
                view_info.view_name,
                view_info.definition
            );
            EXECUTE format(
                'ALTER VIEW public.%I OWNER TO %I',
                view_info.view_name,
                view_info.owner_name
            );
        END LOOP;

        DROP TABLE nested_type_views;
    END;
$body$;

-- revoke permissions for the read-only user
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
REVOKE USAGE ON SCHEMA public FROM PUBLIC;

GRANT CREATE ON SCHEMA public TO {mainuser};
GRANT USAGE ON SCHEMA public TO {mainuser};

GRANT CREATE ON SCHEMA public TO {writeuser};
GRANT USAGE ON SCHEMA public TO {writeuser};

-- take connect permissions from main db
REVOKE CONNECT ON DATABASE {maindb} FROM {readuser};

-- grant select permissions for read-only user
GRANT CONNECT ON DATABASE {datastoredb} TO {readuser};
GRANT USAGE ON SCHEMA public TO {readuser};

-- grant access to current tables and views to read-only user
GRANT SELECT ON ALL TABLES IN SCHEMA public TO {readuser};

-- grant access to new tables and views by default
ALTER DEFAULT PRIVILEGES FOR USER {writeuser} IN SCHEMA public
   GRANT SELECT ON TABLES TO {readuser};

-- a view for listing valid table (resource id) and view names
CREATE OR REPLACE VIEW "_table_metadata" AS
    SELECT DISTINCT
        substr(md5(dependee.relname || COALESCE(dependent.relname, '')), 0, 17) AS "_id",
        dependee.relname AS name,
        dependee.oid AS oid,
        dependent.relname AS alias_of
    FROM
        pg_class AS dependee
        LEFT OUTER JOIN pg_rewrite AS r ON r.ev_class = dependee.oid
        LEFT OUTER JOIN pg_depend AS d ON d.objid = r.oid
        LEFT OUTER JOIN pg_class AS dependent ON d.refobjid = dependent.oid
    WHERE
        (dependee.oid != dependent.oid OR dependent.oid IS NULL) AND
        -- is a table (from pg_tables view definition)
        -- or is a view (from pg_views view definition)
        (dependee.relkind = 'r'::"char" OR dependee.relkind = 'v'::"char")
        AND dependee.relnamespace = (
            SELECT oid FROM pg_namespace WHERE nspname='public')
        AND NOT starts_with(dependee.relname, '_')
    ORDER BY dependee.oid DESC;
ALTER VIEW "_table_metadata" OWNER TO {writeuser};
GRANT SELECT ON "_table_metadata" TO {readuser};

-- _full_text fields are now updated by a trigger when set to NULL
CREATE OR REPLACE FUNCTION populate_full_text_trigger() RETURNS trigger
AS $body$
    BEGIN
        IF NEW._full_text IS NOT NULL THEN
            RETURN NEW;
        END IF;
        NEW._full_text := (
            SELECT to_tsvector(string_agg(value, ' '))
            FROM json_each_text(row_to_json(NEW.*))
            WHERE key NOT LIKE '\_%');
        RETURN NEW;
    END;
$body$ LANGUAGE plpgsql;
ALTER FUNCTION populate_full_text_trigger() OWNER TO {writeuser};

-- migrate existing tables that don't have full text trigger applied
DO $body$
    BEGIN
        EXECUTE coalesce(
            (SELECT string_agg(
                'CREATE TRIGGER zfulltext BEFORE INSERT OR UPDATE ON ' ||
                quote_ident(relname) || ' FOR EACH ROW EXECUTE PROCEDURE ' ||
                'populate_full_text_trigger();', ' ')
            FROM pg_class
            LEFT OUTER JOIN pg_trigger AS t
                ON t.tgrelid = relname::regclass AND t.tgname = 'zfulltext'
            WHERE relkind = 'r'::"char" AND t.tgname IS NULL
                AND relnamespace = (
                    SELECT oid FROM pg_namespace WHERE nspname='public')
                AND NOT starts_with(relname, '_')),
            'SELECT 1;');
    END;
$body$;

-- _table_stats for caching row counts and other useful table statistics
CREATE TABLE IF NOT EXISTS "_table_stats" (
    "resource_id" name PRIMARY KEY,
    "stats" jsonb NOT NULL
);
ALTER TABLE "_table_stats" OWNER TO {writeuser};

CREATE OR REPLACE FUNCTION update_cached_table_row_count(table_name name)
    RETURNS BIGINT
AS $body$
    DECLARE
        row_count BIGINT;
    BEGIN
        EXECUTE format('SELECT count(*) FROM public.%I', table_name)
            INTO row_count;
        INSERT INTO "_table_stats"
            VALUES (table_name, jsonb_build_object('rows', row_count))
            ON CONFLICT ("resource_id") DO UPDATE SET "stats" =
                jsonb_set("_table_stats"."stats", array['rows'], to_jsonb(row_count));
        RETURN row_count;
    END;
$body$ LANGUAGE plpgsql;
ALTER FUNCTION update_cached_table_row_count(name) OWNER TO {writeuser};

CREATE OR REPLACE FUNCTION cached_table_row_count(table_name name)
    RETURNS BIGINT
AS $body$
    DECLARE
        row_count BIGINT;
    BEGIN
        SELECT stats -> 'rows' INTO row_count FROM "_table_stats"
            WHERE "resource_id" = table_name;
        IF row_count IS NULL THEN
            SELECT update_cached_table_row_count(table_name) INTO row_count;
        END IF;
        RETURN row_count;
    END;
$body$ LANGUAGE plpgsql;
ALTER FUNCTION cached_table_row_count(name) OWNER TO {writeuser};

CREATE OR REPLACE FUNCTION update_table_stats(table_name name)
    RETURNS BOOL
AS $body$
    BEGIN
        EXECUTE format('ANALYZE public.%I', table_name);
        PERFORM cached_table_row_count(table_name);
        RETURN TRUE;
    END;
$body$ LANGUAGE plpgsql;
ALTER FUNCTION update_table_stats(name) OWNER TO {writeuser};
