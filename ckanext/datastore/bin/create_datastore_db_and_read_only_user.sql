/*
This script creates a new datastore database and
a new read-only user for ckan who will only be able
to select from the datastore database but has no create/write/edit
permission or any permissions on other databases.

Please set the variables to you current setup. For testing purposes it
is possible to set maindb = datastoredb.

To run the script, execute:
    sudo -u postgres psql postgres -f create_read_only_user.sql
*/

\set maindb "ckan"
-- don't quote the datastoredb variable or create the database separately
\set datastoredb datastore
\set ckanuser ckanuser
\set rouser readonlyuser

-- create the datastore database
create database :datastoredb;

-- switch to the new database
\c :datastoredb;

/*
-- delete the previous users
REVOKE CONNECT ON DATABASE :datastoredb FROM :rouser;
DROP OWNED BY :rouser;
DROP USER :rouser;
--*/

-- revoke permissions for the new user
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
REVOKE USAGE ON SCHEMA public FROM PUBLIC;

GRANT CREATE ON SCHEMA public TO :ckanuser;
GRANT USAGE ON SCHEMA public TO :ckanuser;

-- create new read only user
CREATE USER :rouser NOSUPERUSER NOCREATEDB NOCREATEROLE LOGIN;

-- take connect permissions from main db
REVOKE CONNECT ON DATABASE :maindb FROM :rouser;

-- grant select permissions for read-only user
GRANT CONNECT ON DATABASE :datastoredb TO :rouser;
GRANT USAGE ON SCHEMA public TO :rouser;

-- grant access to current tables and views
GRANT SELECT ON ALL TABLES IN SCHEMA public TO :rouser;

-- grant access to new tables and views by default
ALTER DEFAULT PRIVILEGES FOR USER :ckanuser IN SCHEMA public
   GRANT SELECT ON TABLES TO :rouser;
