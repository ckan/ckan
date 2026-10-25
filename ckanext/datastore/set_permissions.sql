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

-- Build column lists and typed input expressions for record loading.
CREATE OR REPLACE FUNCTION load_record_columns(
    table_name text,
    fields text[]
) RETURNS TABLE (
    column_list text,
    select_values text,
    table_fields text[],
    return_record_values text
)
AS $body$
DECLARE
    field_name text;
    field_type text;
    field_type_name text;
    field_category "char";
    field_index integer := 0;
BEGIN
    column_list := '';
    select_values := '';
    FOREACH field_name IN ARRAY fields LOOP
        field_index := field_index + 1;
        IF field_index > 1 THEN
            column_list := column_list || ', ';
            select_values := select_values || ', ';
        END IF;
        column_list := column_list || format('%I', field_name);

        SELECT format_type(a.atttypid, a.atttypmod), t.typname, t.typcategory
        INTO field_type, field_type_name, field_category
        FROM pg_attribute AS a
        JOIN pg_class AS c ON c.oid = a.attrelid
        JOIN pg_namespace AS n ON n.oid = c.relnamespace
        JOIN pg_type AS t ON t.oid = a.atttypid
        WHERE n.nspname = 'public'
            AND c.relname = table_name
            AND a.attname = field_name
            AND a.attnum > 0
            AND NOT a.attisdropped;

        -- text fields keep empty strings as-is, other types convert empty strings to NULL
        IF field_category = 'S' THEN
            select_values := select_values || format(
                '($1)[__row_num][%s]::%s', field_index, field_type
            );
        ELSE
            select_values := select_values || format(
                'NULLIF(($1)[__row_num][%s], '''')::%s', field_index, field_type
            );
        END IF;
    END LOOP;

    SELECT
        array_agg(a.attname::text ORDER BY a.attnum),
        string_agg(
            format('inserted.%I::text', a.attname),
            ', ' ORDER BY a.attnum
        )
    INTO table_fields, return_record_values
    FROM pg_attribute AS a
    JOIN pg_class AS c ON c.oid = a.attrelid
    JOIN pg_namespace AS n ON n.oid = c.relnamespace
    WHERE n.nspname = 'public'
        AND c.relname = table_name
        AND c.relkind IN ('r', 'p')
        AND a.attnum > 0
        AND NOT a.attisdropped;

    RETURN NEXT;
END;
$body$ LANGUAGE plpgsql STABLE;
ALTER FUNCTION load_record_columns(text, text[]) OWNER TO {writeuser};

-- Return the first unique constraint's columns ("primary_key" in datastore API)
CREATE OR REPLACE FUNCTION first_unique_constraint_columns(table_name text)
RETURNS text[]
AS $body$
    SELECT array_agg(attribute.attname::text ORDER BY key_column.ordinality)
    FROM (
        SELECT constraint_row.conrelid, constraint_row.conkey
        FROM pg_constraint AS constraint_row
        JOIN pg_class AS relation
            ON relation.oid = constraint_row.conrelid
        JOIN pg_namespace AS relation_namespace
            ON relation_namespace.oid = relation.relnamespace
        WHERE relation_namespace.nspname = 'public'
            AND relation.relname = table_name
            AND constraint_row.contype = 'u'
        ORDER BY constraint_row.oid
        LIMIT 1
    ) AS unique_constraint
    CROSS JOIN LATERAL unnest(unique_constraint.conkey)
        WITH ORDINALITY AS key_column(attnum, ordinality)
    JOIN pg_attribute AS attribute
        ON attribute.attrelid = unique_constraint.conrelid
        AND attribute.attnum = key_column.attnum;
$body$ LANGUAGE sql STABLE;
ALTER FUNCTION first_unique_constraint_columns(text) OWNER TO {writeuser};

-- Build the bulk statement for load_records; input rows are passed as $1.
CREATE OR REPLACE FUNCTION load_records_bulk_sql(
    table_name text,
    fields text[],
    key_fields text[],
    operation text,
    return_records boolean,
    column_list text,
    select_values text,
    output_record_values text
) RETURNS text
AS $body$
DECLARE
    update_assignments text := '';
    match_clause text := '';
    conflict_target text := '';
    conflict_key_returning text := '';
    conflict_key_join text := '';
    source_column_list text;
    field_name text;
    key_index integer := 0;
BEGIN
    IF operation = 'insert' AND return_records THEN
        RETURN format(
            'WITH inserted AS (
                INSERT INTO public.%I AS inserted (%s)
                SELECT %s
                FROM generate_subscripts($1, 1) AS __row_num
                ORDER BY __row_num
                RETURNING jsonb_build_array(%s) AS record
            )
            SELECT coalesce(jsonb_agg(record), ''[]''::jsonb) FROM inserted',
            table_name,
            column_list,
            select_values,
            output_record_values
        );
    ELSIF operation = 'insert' THEN
        RETURN format(
            'INSERT INTO public.%I AS inserted (%s)
            SELECT %s
            FROM generate_subscripts($1, 1) AS __row_num
            ORDER BY __row_num',
            table_name,
            column_list,
            select_values
        );
    ELSIF operation = 'update' THEN
        FOREACH field_name IN ARRAY fields LOOP
            IF update_assignments <> '' THEN
                update_assignments := update_assignments || ', ';
            END IF;
            update_assignments := update_assignments ||
                format('%I = source.%I', field_name, field_name);
        END LOOP;
        FOREACH field_name IN ARRAY key_fields LOOP
            IF match_clause <> '' THEN
                match_clause := match_clause || ' AND ';
            END IF;
            match_clause := match_clause || format(
                'target.%I = source.%I', field_name, field_name
            );
        END LOOP;
        source_column_list := '__row_num, ' || column_list;
        IF NOT return_records THEN
            RETURN format(
                'WITH source(%s) AS MATERIALIZED (
                    SELECT __row_num, %s
                    FROM generate_subscripts($1, 1) AS __row_num
                )
                UPDATE public.%I AS target
                SET %s
                FROM source
                WHERE %s',
                source_column_list, select_values, table_name,
                update_assignments, match_clause
            );
        END IF;
        RETURN format(
            'WITH source(%s) AS MATERIALIZED (
                SELECT __row_num, %s
                FROM generate_subscripts($1, 1) AS __row_num
            ),
            updated AS (
                UPDATE public.%I AS target
                SET %s
                FROM source
                WHERE %s
                RETURNING source.__row_num,
                    jsonb_build_array(%s) AS record
            )
            SELECT coalesce(
                jsonb_agg(record ORDER BY __row_num), ''[]''::jsonb
            ), count(*) FROM updated',
            source_column_list, select_values, table_name,
            update_assignments, match_clause,
            replace(output_record_values, 'inserted.', 'target.')
        );
    END IF;

    FOREACH field_name IN ARRAY fields LOOP
        IF update_assignments <> '' THEN
            update_assignments := update_assignments || ', ';
        END IF;
        update_assignments := update_assignments || format(
            '%I = EXCLUDED.%I', field_name, field_name
        );
    END LOOP;
    FOREACH field_name IN ARRAY key_fields LOOP
        IF conflict_target <> '' THEN
            conflict_target := conflict_target || ', ';
            conflict_key_returning := conflict_key_returning || ', ';
            conflict_key_join := conflict_key_join || ' AND ';
        END IF;
        key_index := key_index + 1;
        conflict_target := conflict_target || format('%I', field_name);
        conflict_key_returning := conflict_key_returning || format(
            'inserted.%I AS key_%s', field_name, key_index
        );
        conflict_key_join := conflict_key_join || format(
            'upserted.key_%s IS NOT DISTINCT FROM source.%I',
            key_index, field_name
        );
    END LOOP;
    IF NOT return_records THEN
        RETURN format(
            'INSERT INTO public.%I AS inserted (%s)
            SELECT %s
            FROM generate_subscripts($1, 1) AS __row_num
            ORDER BY __row_num
            ON CONFLICT (%s) DO UPDATE SET %s',
            table_name, column_list, select_values,
            conflict_target, update_assignments
        );
    END IF;
    RETURN format(
        'WITH source(%s) AS MATERIALIZED (
            SELECT __row_num, %s
            FROM generate_subscripts($1, 1) AS __row_num
        ),
        upserted AS (
            INSERT INTO public.%I AS inserted (%s)
            SELECT %s FROM source ORDER BY source.__row_num
            ON CONFLICT (%s) DO UPDATE SET %s
            RETURNING %s,
                jsonb_build_array(%s) AS record
        )
        SELECT coalesce(
            jsonb_agg(upserted.record ORDER BY source.__row_num),
            ''[]''::jsonb
        )
        FROM upserted
        JOIN source ON %s',
        '__row_num, ' || column_list, select_values, table_name,
        column_list, column_list, conflict_target,
        update_assignments, conflict_key_returning,
        output_record_values, conflict_key_join
    );
END;
$body$ LANGUAGE plpgsql IMMUTABLE;
ALTER FUNCTION load_records_bulk_sql(
    text, text[], text[], text, boolean, text, text, text
) OWNER TO {writeuser};

-- Load input rows and return inserted/updated records or row errors.
CREATE OR REPLACE FUNCTION load_records(
    table_name text,
    fields text[],
    rows text[][],
    stop_on_error boolean DEFAULT false,
    return_records boolean DEFAULT true,
    operation text DEFAULT 'insert'
) RETURNS jsonb
AS $body$
DECLARE
    all_fields text[];
    output_record_values text;
    column_list text;
    select_values text;
    bulk_sql text;
    row_sql text;
    null_key_clause text;
    key_fields text[];
    has_null_key boolean;
    affected_rows integer;
    output_records jsonb := '[]'::jsonb;
    fallback_table text;
    bulk_error text;
    errors jsonb;
    unique_fields text[];
BEGIN
    IF operation NOT IN ('insert', 'update', 'upsert') THEN
        RETURN jsonb_build_array(
            jsonb_build_array(0, format('Unknown operation: %s', operation))
        );
    END IF;

    SELECT columns.column_list, columns.select_values,
        columns.table_fields, columns.return_record_values
    INTO column_list, select_values, all_fields, output_record_values
    FROM load_record_columns(table_name, fields) AS columns;

    IF operation IN ('update', 'upsert') THEN
        unique_fields := first_unique_constraint_columns(table_name);
        IF array_position(fields, '_id') IS NOT NULL THEN
            key_fields := ARRAY['_id'];
        ELSIF unique_fields IS NOT NULL AND fields @> unique_fields THEN
            key_fields := unique_fields;
        ELSE
            RAISE EXCEPTION 'No key fields provided for %', operation;
        END IF;
    END IF;

    bulk_sql := load_records_bulk_sql(
        table_name, fields, key_fields, operation, return_records,
        column_list, select_values, output_record_values
    );

    -- fast path: bulk insert/update/upsert
    BEGIN
        IF operation = 'insert' AND return_records THEN
            EXECUTE bulk_sql INTO output_records USING rows;
        ELSIF operation = 'insert' THEN
            EXECUTE bulk_sql USING rows;
        ELSIF operation = 'update' THEN
            IF return_records THEN
                EXECUTE bulk_sql INTO output_records, affected_rows
                    USING rows;
            ELSE
                EXECUTE bulk_sql USING rows;
                GET DIAGNOSTICS affected_rows = ROW_COUNT;
            END IF;
            IF affected_rows <> coalesce(array_length(rows, 1), 0) THEN
                RAISE EXCEPTION 'Not all rows matched for update';
            END IF;
            RETURN jsonb_build_object(
                'records', CASE
                    WHEN return_records THEN output_records
                    ELSE 'null'::jsonb
                END,
                'fields', to_jsonb(all_fields)
            );
        ELSIF operation = 'upsert' THEN
            IF return_records THEN
                SELECT string_agg(format('source.%I IS NULL', key_field), ' OR ')
                INTO null_key_clause
                FROM unnest(key_fields) AS key_field;
                EXECUTE format(
                    'SELECT EXISTS (
                        SELECT 1 FROM (
                            SELECT %s FROM generate_subscripts($1, 1) AS __row_num
                        ) AS source(%s)
                        WHERE %s
                    )',
                    select_values, column_list, null_key_clause
                ) INTO has_null_key USING rows;
                IF has_null_key THEN
                    RAISE EXCEPTION
                        'Cannot batch upsert rows with NULL conflict keys';
                END IF;
                EXECUTE bulk_sql INTO output_records USING rows;
            ELSE
                EXECUTE bulk_sql USING rows;
            END IF;
            RETURN jsonb_build_object(
                'records', CASE
                    WHEN return_records THEN output_records
                    ELSE 'null'::jsonb
                END,
                'fields', to_jsonb(all_fields)
            );
        END IF;
        IF operation = 'insert' THEN
            RETURN jsonb_build_object(
                'records', CASE
                    WHEN return_records THEN output_records
                    ELSE 'null'::jsonb
                END,
                'fields', to_jsonb(all_fields)
            );
        END IF;
    EXCEPTION WHEN OTHERS THEN
        bulk_error := SQLERRM;
    END;

    -- fallback: collect error(s) and row index(es) to return to caller
    fallback_table := format(
        'load_records_%s_%s', pg_backend_pid(), txid_current()
    );
    EXECUTE format(
        'CREATE TEMP TABLE %I (
            row_idx integer,
            error_message text
        ) ON COMMIT DROP',
        fallback_table
    );

    row_sql := load_records_bulk_sql(
        table_name, fields, key_fields, operation, false,
        column_list, select_values, output_record_values
    );

    BEGIN
        FOR row_idx IN 0..coalesce(array_length(rows, 1), 0) - 1 LOOP
            BEGIN
                EXECUTE row_sql USING rows[row_idx + 1:row_idx + 1];
                IF operation = 'update' THEN
                    GET DIAGNOSTICS affected_rows = ROW_COUNT;
                    IF affected_rows = 0 THEN
                        RAISE EXCEPTION 'No matching record found for update';
                    END IF;
                END IF;
            EXCEPTION WHEN OTHERS THEN
                EXECUTE format(
                    'INSERT INTO pg_temp.%I (row_idx, error_message) VALUES ($1, $2)',
                    fallback_table
                ) USING row_idx, SQLERRM;
                IF stop_on_error THEN
                    EXIT;
                END IF;
            END;
        END LOOP;

        EXECUTE format(
            'SELECT
                jsonb_agg(jsonb_build_array(row_idx, error_message)
                    ORDER BY row_idx)
                    FILTER (WHERE error_message IS NOT NULL)
            FROM pg_temp.%I',
            fallback_table
        ) INTO errors;
        IF errors IS NULL THEN
            errors := jsonb_build_array(jsonb_build_array(0, bulk_error));
        END IF;
        -- raising rolls back any rows the fallback loop managed to load
        RAISE SQLSTATE 'PZ001';
    EXCEPTION WHEN SQLSTATE 'PZ001' THEN
        EXECUTE format('DROP TABLE pg_temp.%I', fallback_table);
        RETURN errors;
    END;
END;
$body$ LANGUAGE plpgsql;
ALTER FUNCTION load_records(
    text, text[], text[][], boolean, boolean, text
) OWNER TO {writeuser};
