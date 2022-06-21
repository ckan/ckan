#!/bin/bash
set -e

# Setup environment
: ${CKAN_INI:=test-core-docker.ini}
export CKAN_INI
source "$CKAN_VENV/bin/activate"

# Wait for PostgreSQL
while ! pg_isready -h db -U postgres; do
  sleep 1;
done

# Initialize PostgreSQL
(
  ckan -c test-core-docker.ini datastore set-permissions
  echo "CREATE extension tablefunc"
) 2>/dev/null | psql postgresql://postgres:pass@db/postgres
ckan --config "$CKAN_INI" db init

# Unset variables used at build time as they interfere with PyTest
unset CKAN_CONFIG
unset CKAN_STORAGE_PATH
unset CKAN_HOME
unset CKAN_VENV

# Run CMD
exec "$@"
