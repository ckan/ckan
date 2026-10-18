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

CREATE OR REPLACE FUNCTION datastore_insert(
    p_table_name text,
    p_fields text[],
    p_rows text[][]
) RETURNS jsonb
AS $body$
DECLARE
    all_fields text[];
    output_values text;
    current_fields text[];
    row_number integer := 1;
    field_index integer := 0;
    column_name text;
    column_list text;
    value_list text;
    select_values text;
    insert_sql text;
    inserted_record jsonb;
    output_record jsonb;
    output_records jsonb := '[]'::jsonb;
    fallback_records jsonb;
    fallback_table text;
    errors jsonb;
BEGIN
    SELECT
        array_agg(a.attname::text ORDER BY a.attnum),
        string_agg(
            format('%L, inserted.%I::text', a.attname, a.attname),
            ', ' ORDER BY a.attnum
        )
    INTO all_fields, output_values
    FROM pg_attribute AS a
    JOIN pg_class AS c ON c.oid = a.attrelid
    JOIN pg_namespace AS n ON n.oid = c.relnamespace
    WHERE n.nspname = 'public'
        AND c.relname = p_table_name
        AND c.relkind IN ('r', 'p')
        AND a.attnum > 0
        AND NOT a.attisdropped;

    IF all_fields IS NULL THEN
        RETURN jsonb_build_object(
            '1', format('Table "%s" does not exist in schema public', p_table_name)
        );
    END IF;
    column_list := '';
    select_values := '';
    FOREACH column_name IN ARRAY p_fields LOOP
        field_index := field_index + 1;
        IF column_list <> '' THEN
            column_list := column_list || ', ';
            select_values := select_values || ', ';
        END IF;
        column_list := column_list || format('%I', column_name);

        SELECT format_type(a.atttypid, a.atttypmod)
        INTO value_list
        FROM pg_attribute AS a
        JOIN pg_class AS c ON c.oid = a.attrelid
        JOIN pg_namespace AS n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public'
            AND c.relname = p_table_name
            AND a.attname = column_name
            AND a.attnum > 0
            AND NOT a.attisdropped;

        select_values := select_values || format(
            '($1)[row_idx][%s]::%s',
            field_index,
            value_list
        );
    END LOOP;

    insert_sql := format(
        'WITH inserted AS (
            INSERT INTO public.%I AS inserted (%s)
            SELECT %s
            FROM generate_subscripts($1, 1) AS row_idx
            ORDER BY row_idx
            RETURNING jsonb_build_array(%s) AS record
        )
        SELECT coalesce(jsonb_agg(record), ''[]''::jsonb) FROM inserted',
        p_table_name,
        column_list,
        select_values,
        (
            SELECT string_agg(
                format('inserted.%I::text', field_name),
                ', ' ORDER BY ordinal
            )
            FROM unnest(all_fields) WITH ORDINALITY
                AS output_fields(field_name, ordinal)
        )
    );

    BEGIN
        EXECUTE insert_sql INTO output_records USING p_rows;
        RETURN jsonb_build_object(
            'records', output_records,
            'fields', to_jsonb(all_fields)
        );
    EXCEPTION WHEN OTHERS THEN
        NULL;
    END;

    fallback_table := format(
        'datastore_insert_%s_%s',
        pg_backend_pid(),
        txid_current()
    );
    EXECUTE format(
        'CREATE TEMP TABLE %I (
            row_num integer,
            record jsonb,
            error_message text
        ) ON COMMIT DROP',
        fallback_table
    );

    BEGIN
        FOREACH current_fields SLICE 1 IN ARRAY p_rows LOOP
            BEGIN
                SELECT string_agg(quote_nullable(value), ', ' ORDER BY ordinal)
                INTO value_list
                FROM unnest(current_fields)
                    WITH ORDINALITY AS values_list(value, ordinal);

                insert_sql := format(
                    'INSERT INTO public.%I AS inserted (%s) VALUES (%s) RETURNING jsonb_build_object(VARIADIC ARRAY[%s])',
                    p_table_name, column_list, value_list, output_values
                );
                EXECUTE insert_sql INTO inserted_record;

                output_record := (
                    SELECT jsonb_agg(inserted_record -> field_name ORDER BY ordinal)
                    FROM unnest(all_fields) WITH ORDINALITY
                        AS output_fields(field_name, ordinal)
                );
                EXECUTE format(
                    'INSERT INTO pg_temp.%I (row_num, record) VALUES ($1, $2)',
                    fallback_table
                ) USING row_number, output_record;
            EXCEPTION WHEN OTHERS THEN
                EXECUTE format(
                    'INSERT INTO pg_temp.%I (row_num, error_message) VALUES ($1, $2)',
                    fallback_table
                ) USING row_number, SQLERRM;
            END;
            row_number := row_number + 1;
        END LOOP;

        EXECUTE format(
            'SELECT
                jsonb_agg(record ORDER BY row_num)
                    FILTER (WHERE error_message IS NULL),
                jsonb_object_agg(row_num::text, error_message)
                    FILTER (WHERE error_message IS NOT NULL)
            FROM pg_temp.%I',
            fallback_table
        ) INTO fallback_records, errors;

        IF errors IS NOT NULL THEN
            RAISE SQLSTATE 'PZ001';
        END IF;
    EXCEPTION WHEN SQLSTATE 'PZ001' THEN
        EXECUTE format('DROP TABLE pg_temp.%I', fallback_table);
        RETURN errors;
    WHEN OTHERS THEN
        EXECUTE format('DROP TABLE pg_temp.%I', fallback_table);
        RAISE;
    END;

    EXECUTE format('DROP TABLE pg_temp.%I', fallback_table);
    RETURN jsonb_build_object(
        'records', coalesce(fallback_records, '[]'::jsonb),
        'fields', to_jsonb(all_fields)
    );
END;
$body$ LANGUAGE plpgsql;
ALTER FUNCTION datastore_insert(text, text[], text[]) OWNER TO {writeuser};
