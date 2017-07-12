#!/bin/bash
set -e
echo "Creating datastore readonly user and database in image db..."
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
    CREATE USER datastore_ro LOGIN NOCREATEDB NOSUPERUSER NOCREATEROLE ENCRYPTED PASSWORD "$DS_RO_PASS";
    CREATE DATABASE datastore OWNER ckan ENCODING utf-8;
    GRANT ALL PRIVILEGES ON DATABASE datastore TO ckan;
EOSQL
echo"done."
#sudo -u postgres createuser -S -D -R -P -l datastore_ro
