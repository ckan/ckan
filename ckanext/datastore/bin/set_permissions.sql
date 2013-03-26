/*
This script sets-up the permissions for the the datastore.

creates a new datastore database and
a new read-only user for ckan who will only be able
to select from the datastore database but has no create/write/edit
permission or any permissions on other databases.

Please set the variables to you current set-up. For testing purposes it
is possible to set maindb = datastoredb.

To run the script, execute:
    sudo -u postgres psql postgres -f set_permissions.sql
*/

-- name of the main CKAN database
\set maindb "{ckandb}"
-- the name of the datastore database
\set datastoredb "{datastoredb}"
-- username of the ckan postgres user
\set ckanuser "{ckanuser}"
-- username of the datastore user that can write
\set wuser "{writeuser}"
-- username of the datastore user who has only read permissions
\set rouser "{readonlyuser}"

-- revoke permissions for the read-only user
---- this step can be ommitted if the datastore not
---- on the same server as the CKAN database
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
REVOKE USAGE ON SCHEMA public FROM PUBLIC;

GRANT CREATE ON SCHEMA public TO :ckanuser;
GRANT USAGE ON SCHEMA public TO :ckanuser;

GRANT CREATE ON SCHEMA public TO :wuser;
GRANT USAGE ON SCHEMA public TO :wuser;

-- take connect permissions from main CKAN db
---- again, this can be ommited if the read-only user can never have
---- access to the main CKAN database
REVOKE CONNECT ON DATABASE :maindb FROM :rouser;

-- grant select permissions for read-only user
GRANT CONNECT ON DATABASE :datastoredb TO :rouser;
GRANT USAGE ON SCHEMA public TO :rouser;

-- grant access to current tables and views to read-only user
GRANT SELECT ON ALL TABLES IN SCHEMA public TO :rouser;

-- grant access to new tables and views by default
---- the permissions will be set when the write user creates a table
ALTER DEFAULT PRIVILEGES FOR USER :wuser IN SCHEMA public
   GRANT SELECT ON TABLES TO :rouser;
