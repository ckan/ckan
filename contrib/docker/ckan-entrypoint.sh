#!/bin/sh
set -e

# URL for the primary database, in the format expected by sqlalchemy (required
# unless linked to a container called 'db')
: ${CKAN_SQLALCHEMY_URL:=}
# URL for solr (required unless linked to a container called 'solr')
: ${CKAN_SOLR_URL:=}
# URL for redis (required unless linked to a container called 'redis')
: ${CKAN_REDIS_URL:=}
# URL for datapusher (required unless linked to a container called 'datapusher')
: ${CKAN_DATAPUSHER_URL:=}

CONFIG="${CKAN_CONFIG}/ckan.ini"

abort () {
  echo "$@" >&2
  exit 1
}

set_environment () {
  export CKAN_SITE_ID=${CKAN_SITE_ID}
  export CKAN_SITE_URL=${CKAN_SITE_URL}
  export CKAN_SQLALCHEMY_URL=${CKAN_SQLALCHEMY_URL}
  export CKAN_SOLR_URL=${CKAN_SOLR_URL}
  export CKAN_REDIS_URL=${CKAN_REDIS_URL}
  export CKAN_STORAGE_PATH=/var/lib/ckan
  export CKAN_DATAPUSHER_URL=${CKAN_DATAPUSHER_URL}
  export CKAN_DATASTORE_WRITE_URL=postgresql://ckan:${POSTGRES_PASSWORD}@db/datastore
  export CKAN_DATASTORE_READ_URL=postgresql://datastore_ro:${DS_RO_PASS}@db/datastore
  export CKAN_SMTP_SERVER=${CKAN_SMTP_SERVER}
  export CKAN_SMTP_STARTTLS=${CKAN_SMTP_STARTTLS}
  export CKAN_SMTP_USER=${CKAN_SMTP_USER}
  export CKAN_SMTP_PASSWORD=${CKAN_SMTP_PASSWORD}
  export CKAN_SMTP_MAIL_FROM=${CKAN_SMTP_MAIL_FROM}
}


write_config () {
  # Note that this only gets called if there is no config, see below!
  ckan-paster make-config --no-interactive ckan "$CONFIG"

  # The variables above will be used by CKAN, but
  # in case want to use the config from ckan.ini use this
  #ckan-paster --plugin=ckan config-tool "$CONFIG" -e \
  #    "sqlalchemy.url = ${CKAN_SQLALCHEMY_URL}" \
  #    "solr_url = ${CKAN_SOLR_URL}" \
  #    "ckan.redis.url = ${CKAN_REDIS_URL}" \
  #    "ckan.storage_path = ${CKAN_STORAGE_PATH}" \
  #    "ckan.site_url = ${CKAN_SITE_URL}"
}

link_postgres_url () {
  local user=$DB_ENV_POSTGRES_USER
  local pass=$DB_ENV_POSTGRES_PASSWORD
  local db=$DB_ENV_POSTGRES_DB
  local host=$DB_PORT_5432_TCP_ADDR
  local port=$DB_PORT_5432_TCP_PORT
  echo "postgresql://${user}:${pass}@${host}:${port}/${db}"
}

link_solr_url () {
  local host=$SOLR_PORT_8983_TCP_ADDR
  local port=$SOLR_PORT_8983_TCP_PORT
  echo "http://${host}:${port}/solr/ckan"
}

link_redis_url () {
  local host=$REDIS_PORT_6379_TCP_ADDR
  local port=$REDIS_PORT_6379_TCP_PORT
  echo "redis://${host}:${port}/1"
}

link_datapusher_url() {
  local host=$DATAPUSHER_PORT_8800_ADDR
  local port=$DATAPUSHER_PORT_8800_PORT
  echo "http://${host}:${port}"

}

# If we don't already have a config file, bootstrap
if [ ! -e "$CONFIG" ]; then
  write_config
fi

# Get or create CKAN_SQLALCHEMY_URL
if [ -z "$CKAN_SQLALCHEMY_URL" ]; then
  if ! CKAN_SQLALCHEMY_URL=$(link_postgres_url); then
    abort "ERROR: no CKAN_SQLALCHEMY_URL specified and linked container called 'db' was not found"
  else
    #If that worked, use the DB details to wait for the DB
    export PGHOST=${DB_PORT_5432_TCP_ADDR}
    export PGPORT=${DB_PORT_5432_TCP_PORT}
    export PGDATABASE=${DB_ENV_POSTGRES_DB}
    export PGUSER=${DB_ENV_POSTGRES_USER}
    export PGPASSWORD=${DB_ENV_POSTGRES_PASSWORD}
    echo "CKAN_SQLALCHEMY_URL: $CKAN_SQLALCHEMY_URL"

    # Give the db container time to initialize the db cluster (if first run)
    for tries in $(seq 60); do
      psql -c 'SELECT 1;' 2> /dev/null && break
      sleep 0.3
    done
  fi
fi

if [ -z "$CKAN_SOLR_URL" ]; then
  if ! CKAN_SOLR_URL=$(link_solr_url); then
    abort "ERROR: no CKAN_SOLR_URL specified and no linked container called 'solr' found"
  fi
fi

if [ -z "$CKAN_REDIS_URL" ]; then
  if ! CKAN_REDIS_URL=$(link_redis_url); then
    abort "ERROR: no CKAN_REDIS_URL specified and no linked container called 'redis' found"
  fi
fi

if [ -z "$CKAN_DATAPUSHER_URL" ]; then
  if ! CKAN_DATAPUSHER_URL=$(link_datapusher_url); then
    abort "ERROR: no CKAN_DATAPUSHER_URL specified and no linked container called 'datapusher' found"
  fi
fi

set_environment

# Initializes the Database
ckan-paster --plugin=ckan db init -c "${CKAN_CONFIG}/ckan.ini"

exec "$@"
