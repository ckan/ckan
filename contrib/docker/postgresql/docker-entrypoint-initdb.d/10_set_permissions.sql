/*
This script configures the permissions for the datastore.

It ensures that the datastore read-only user will only be able to select from
the datastore database but has no create/write/edit permission or any
permissions on other databases. You must execute this script as a database
superuser on the PostgreSQL server that hosts your datastore database.

For example, if PostgreSQL is running locally and the "postgres" user has the
appropriate permissions (as in the default Ubuntu PostgreSQL install), you can
run:

    paster datastore set-permissions | sudo -u postgres psql

Or, if your PostgreSQL server is remote, you can pipe the permissions script
over SSH:

    paster datastore set-permissions | ssh dbserver sudo -u postgres psql

*/

-- Most of the following commands apply to an explicit database or to the whole
-- 'public' schema, and could be executed anywhere. But ALTER DEFAULT
-- PERMISSIONS applies to the current database, and so we must be connected to
-- the datastore DB:
\connect "datastore"

-- revoke permissions for the read-only user
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
REVOKE USAGE ON SCHEMA public FROM PUBLIC;

GRANT CREATE ON SCHEMA public TO "ckan";
GRANT USAGE ON SCHEMA public TO "ckan";

GRANT CREATE ON SCHEMA public TO "ckan";
GRANT USAGE ON SCHEMA public TO "ckan";

-- take connect permissions from main db
REVOKE CONNECT ON DATABASE "ckan" FROM "datastore_ro";

-- grant select permissions for read-only user
GRANT CONNECT ON DATABASE "datastore" TO "datastore_ro";
GRANT USAGE ON SCHEMA public TO "datastore_ro";

-- grant access to current tables and views to read-only user
GRANT SELECT ON ALL TABLES IN SCHEMA public TO "datastore_ro";

-- grant access to new tables and views by default
ALTER DEFAULT PRIVILEGES FOR USER "ckan" IN SCHEMA public
   GRANT SELECT ON TABLES TO "datastore_ro";

CREATE OR REPLACE VIEW "_table_metadata" AS
    SELECT DISTINCT
        substr(md5(dependee.relname || COALESCE(dependent.relname, '')), 0, 17) AS "_id",
        dependee.relname AS name,
        dependee.oid AS oid,
        dependent.relname AS alias_of
        -- dependent.oid AS oid
    FROM
        pg_class AS dependee
        LEFT OUTER JOIN pg_rewrite AS r ON r.ev_class = dependee.oid
        LEFT OUTER JOIN pg_depend AS d ON d.objid = r.oid
        LEFT OUTER JOIN pg_class AS dependent ON d.refobjid = dependent.oid
    WHERE
        (dependee.oid != dependent.oid OR dependent.oid IS NULL) AND
        (dependee.relname IN (SELECT tablename FROM pg_catalog.pg_tables)
            OR dependee.relname IN (SELECT viewname FROM pg_catalog.pg_views)) AND
        dependee.relnamespace = (SELECT oid FROM pg_namespace WHERE nspname='public')
    ORDER BY dependee.oid DESC;
ALTER VIEW "_table_metadata" OWNER TO "ckan";
GRANT SELECT ON "_table_metadata" TO "datastore_ro";

