#!/bin/sh
set -e

# URL for the primary database, in the format expected by sqlalchemy (required
# unless linked to a container called 'db')
: ${CKAN_SQLALCHEMY_URL:=}
# URL for solr (required unless linked to a container called 'solr')
: ${CKAN_SOLR_URL:=}
# URL for redis (required unless linked to a container called 'redis')
: ${CKAN_REDIS_URL:=}

CONFIG="${CKAN_CONFIG}/ckan.ini"

abort () {
  echo "$@" >&2
  exit 1
}

write_config () {

  export CKAN_SQLALCHEMY_URL=${CKAN_SQLALCHEMY_URL}
  export CKAN_SOLR_URL=${CKAN_SOLR_URL}
  export CKAN_REDIS_URL=${CKAN_REDIS_URL}
  export CKAN_STORAGE_PATH=${CKAN_STORAGE_PATH}
  export CKAN_SITE_URL=${CKAN_SITE_URL}

  ckan-paster make-config ckan "$CONFIG"

  # Apply config
  ckan-paster --plugin=ckan config-tool "$CONFIG" -e \
      "sqlalchemy.url = ${CKAN_SQLALCHEMY_URL}" \
      "solr_url = ${CKAN_SOLR_URL}" \
      "ckan.redis.url = ${CKAN_REDIS_URL}" \
      "ckan.storage_path = ${CKAN_STORAGE_PATH}" \
      "ckan.site_url = ${CKAN_SITE_URL}"
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

# If we don't already have a config file, bootstrap
if [ ! -e "$CONFIG" ]; then

  if [ -z "$CKAN_SQLALCHEMY_URL" ]; then
    if ! CKAN_SQLALCHEMY_URL=$(link_postgres_url); then
      abort "ERROR: no CKAN_SQLALCHEMY_URL specified and linked container called 'db' was not found"
    fi
  fi

  if [ -z "$CKAN_SOLR_URL" ]; then
    if ! CKAN_SOLR_URL=$(link_solr_url); then
      abort "ERROR: no CKAN_SOLR_URL specified and linked container called 'solr' was not found"
    fi
  fi
    
  if [ -z "$CKAN_REDIS_URL" ]; then
    if ! CKAN_REDIS_URL=$(link_redis_url); then
      abort "ERROR: no CKAN_REDIS_URL specified and linked container called 'redis' was not found"
    fi
  fi

  write_config

fi

# Initializes the Database
ckan-paster --plugin=ckan db init -c "${CKAN_CONFIG}/ckan.ini"

exec "$@"
