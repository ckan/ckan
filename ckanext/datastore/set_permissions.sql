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
    fallback_values text,
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
    fallback_values := '';
    FOREACH field_name IN ARRAY fields LOOP
        field_index := field_index + 1;
        IF field_index > 1 THEN
            column_list := column_list || ', ';
            select_values := select_values || ', ';
            fallback_values := fallback_values || ', ';
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

        IF field_category = 'S' THEN
            select_values := select_values || format(
                '($1)[row_idx][%s]::%s', field_index, field_type
            );
            fallback_values := fallback_values || format(
                '($1)[%s]::%s', field_index, field_type
            );
        ELSIF field_type_name IN ('json', 'jsonb') THEN
            select_values := select_values || format(
                '(CASE WHEN ($1)[row_idx][%s] = '''' THEN to_json(($1)[row_idx][%s]) ELSE ($1)[row_idx][%s]::json END)::%s',
                field_index, field_index, field_index, field_type
            );
            fallback_values := fallback_values || format(
                '(CASE WHEN ($1)[%s] = '''' THEN to_json(($1)[%s]) ELSE ($1)[%s]::json END)::%s',
                field_index, field_index, field_index, field_type
            );
        ELSE
            select_values := select_values || format(
                'NULLIF(($1)[row_idx][%s], '''')::%s', field_index, field_type
            );
            fallback_values := fallback_values || format(
                'NULLIF(($1)[%s], '''')::%s', field_index, field_type
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

-- Return the first unique constraint's columns in constraint key order.
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

-- Apply one input row using insert, update, or upsert semantics.
DROP FUNCTION IF EXISTS load_record_row(
    text, text[], text[], text, text[], text, text, text, boolean
);
CREATE OR REPLACE FUNCTION load_record_row(
    table_name text,
    fields text[],
    current_fields text[],
    operation text,
    unique_fields text[],
    column_list text,
    fallback_values text
) RETURNS void
AS $body$
DECLARE
    key_fields text[];
    field_name text;
    match_clause text;
    conflict_target text := '';
    update_assignments text := '';
    update_sql text;
    insert_sql text;
    affected_rows integer := 0;
BEGIN
    IF operation = 'upsert' THEN
        IF array_position(fields, '_id') IS NOT NULL THEN
            key_fields := ARRAY['_id'];
        ELSIF unique_fields IS NOT NULL
            AND fields @> unique_fields THEN
            key_fields := unique_fields;
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
            END IF;
            conflict_target := conflict_target || format('%I', field_name);
        END LOOP;
        insert_sql := format(
            'INSERT INTO public.%I AS inserted (%s)
            SELECT %s
            ON CONFLICT (%s) DO UPDATE SET %s',
            table_name, column_list, fallback_values,
            conflict_target, update_assignments
        );
        EXECUTE insert_sql USING current_fields;
        RETURN;
    END IF;

    IF operation = 'update' THEN
        IF array_position(fields, '_id') IS NOT NULL THEN
            key_fields := ARRAY['_id'];
        ELSIF unique_fields IS NOT NULL
            AND fields @> unique_fields THEN
            key_fields := unique_fields;
        END IF;
        FOREACH field_name IN ARRAY fields LOOP
            IF update_assignments <> '' THEN
                update_assignments := update_assignments || ', ';
            END IF;
            update_assignments := update_assignments ||
                format('%I = source.%I', field_name, field_name);
        END LOOP;

        IF key_fields IS NOT NULL THEN
            match_clause := '';
            FOREACH field_name IN ARRAY key_fields LOOP
                IF match_clause <> '' THEN
                    match_clause := match_clause || ' AND ';
                END IF;
                match_clause := match_clause || format(
                    'target.%I = source.%I',
                    field_name, field_name
                );
            END LOOP;

            update_sql := format(
                'UPDATE public.%I AS target
                    SET %s
                    FROM (SELECT %s) AS source(%s)
                    WHERE %s',
                table_name,
                update_assignments,
                fallback_values,
                column_list,
                match_clause
            );
            EXECUTE update_sql USING current_fields;
            GET DIAGNOSTICS affected_rows = ROW_COUNT;
            IF affected_rows > 0 THEN
                RETURN;
            END IF;
        END IF;

        RAISE EXCEPTION 'No matching record found for update';
    END IF;

    IF operation = 'insert' THEN
        insert_sql := format(
            'INSERT INTO public.%I AS inserted (%s) SELECT %s',
            table_name, column_list, fallback_values
        );
        EXECUTE insert_sql USING current_fields;
    END IF;
END;
$body$ LANGUAGE plpgsql;
ALTER FUNCTION load_record_row(
    text, text[], text[], text, text[], text, text
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
    current_fields text[];
    row_number integer := 0;
    column_list text;
    select_values text;
    fallback_values text;
    insert_sql text;
    update_sql text;
    update_assignments text := '';
    match_clause text := '';
    conflict_target text := '';
    conflict_key_returning text := '';
    conflict_key_join text := '';
    null_key_clause text := '';
    source_column_list text;
    field_name text;
    key_fields text[];
    key_index integer := 0;
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
        columns.fallback_values, columns.table_fields,
        columns.return_record_values
    INTO column_list, select_values, fallback_values, all_fields,
        output_record_values
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

    IF operation = 'insert' AND return_records THEN
        insert_sql := format(
            'WITH inserted AS (
                INSERT INTO public.%I AS inserted (%s)
                SELECT %s
                FROM generate_subscripts($1, 1) AS row_idx
                ORDER BY row_idx
                RETURNING jsonb_build_array(%s) AS record
            )
            SELECT coalesce(jsonb_agg(record), ''[]''::jsonb) FROM inserted',
            table_name,
            column_list,
            select_values,
            output_record_values
        );
    ELSIF operation = 'insert' THEN
        insert_sql := format(
            'INSERT INTO public.%I AS inserted (%s)
            SELECT %s
            FROM generate_subscripts($1, 1) AS row_idx
            ORDER BY row_idx',
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
        source_column_list := 'row_num, ' || column_list;
        update_sql := format(
            'WITH source(%s) AS MATERIALIZED (
                SELECT row_idx, %s
                FROM generate_subscripts($1, 1) AS row_idx
            ),
            updated AS (
                UPDATE public.%I AS target
                SET %s
                FROM source
                WHERE %s
                RETURNING source.row_num,
                    jsonb_build_array(%s) AS record
            )
            SELECT coalesce(
                jsonb_agg(record ORDER BY row_num), ''[]''::jsonb
            ), count(*) FROM updated',
            source_column_list, select_values, table_name,
            update_assignments, match_clause,
            replace(output_record_values, 'inserted.', 'target.')
        );
        IF NOT return_records THEN
            update_sql := format(
                'WITH source(%s) AS MATERIALIZED (
                    SELECT row_idx, %s
                    FROM generate_subscripts($1, 1) AS row_idx
                )
                UPDATE public.%I AS target
                SET %s
                FROM source
                WHERE %s',
                source_column_list, select_values, table_name,
                update_assignments, match_clause
            );
        END IF;
    ELSIF operation = 'upsert' THEN
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
                null_key_clause := null_key_clause || ' OR ';
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
            null_key_clause := null_key_clause || format(
                'source.%I IS NULL', field_name
            );
        END LOOP;
        IF return_records THEN
            source_column_list := 'row_num, ' || column_list;
            insert_sql := format(
                'WITH source(%s) AS MATERIALIZED (
                    SELECT row_idx, %s
                    FROM generate_subscripts($1, 1) AS row_idx
                ),
                upserted AS (
                    INSERT INTO public.%I AS inserted (%s)
                    SELECT %s FROM source ORDER BY source.row_num
                    ON CONFLICT (%s) DO UPDATE SET %s
                    RETURNING %s,
                        jsonb_build_array(%s) AS record
                )
                SELECT coalesce(
                    jsonb_agg(upserted.record ORDER BY source.row_num),
                    ''[]''::jsonb
                )
                FROM upserted
                JOIN source ON %s',
                source_column_list, select_values, table_name,
                column_list, column_list, conflict_target,
                update_assignments, conflict_key_returning,
                output_record_values, conflict_key_join
            );
        ELSE
            insert_sql := format(
                'INSERT INTO public.%I AS inserted (%s)
                SELECT %s
                FROM generate_subscripts($1, 1) AS row_idx
                ORDER BY row_idx
                ON CONFLICT (%s) DO UPDATE SET %s',
                table_name, column_list, select_values,
                conflict_target, update_assignments
            );
        END IF;
    END IF;

    BEGIN
        IF operation = 'insert' AND return_records THEN
            EXECUTE insert_sql INTO output_records USING rows;
        ELSIF operation = 'insert' THEN
            EXECUTE insert_sql USING rows;
        ELSIF operation = 'update' THEN
            IF return_records THEN
                EXECUTE update_sql INTO output_records, affected_rows
                    USING rows;
            ELSE
                EXECUTE update_sql USING rows;
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
                EXECUTE format(
                    'SELECT EXISTS (
                        SELECT 1 FROM (
                            SELECT %s FROM generate_subscripts($1, 1) AS row_idx
                        ) AS source(%s)
                        WHERE %s
                    )',
                    select_values, column_list, null_key_clause
                ) INTO has_null_key USING rows;
                IF has_null_key THEN
                    RAISE EXCEPTION
                        'Cannot batch upsert rows with NULL conflict keys';
                END IF;
                EXECUTE insert_sql INTO output_records USING rows;
            ELSE
                EXECUTE insert_sql USING rows;
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

    -- collect error(s) and row_number(s) to return to caller
    fallback_table := format(
        'load_records_%s_%s', pg_backend_pid(), txid_current()
    );
    EXECUTE format(
        'CREATE TEMP TABLE %I (
            row_num integer,
            error_message text
        ) ON COMMIT DROP',
        fallback_table
    );

    BEGIN
        FOREACH current_fields SLICE 1 IN ARRAY rows LOOP
            BEGIN
                PERFORM load_record_row(
                    table_name,
                    fields,
                    current_fields,
                    operation,
                    unique_fields,
                    column_list,
                    fallback_values
                );
            EXCEPTION WHEN OTHERS THEN
                EXECUTE format(
                    'INSERT INTO pg_temp.%I (row_num, error_message) VALUES ($1, $2)',
                    fallback_table
                ) USING row_number, SQLERRM;
                IF stop_on_error THEN
                    EXIT;
                END IF;
            END;
            row_number := row_number + 1;
        END LOOP;

        EXECUTE format(
            'SELECT
                jsonb_agg(jsonb_build_array(row_num, error_message)
                    ORDER BY row_num)
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
