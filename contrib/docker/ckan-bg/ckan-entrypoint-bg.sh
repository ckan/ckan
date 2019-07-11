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

CONFIG="${CKAN_CONFIG}/production.ini"

abort() {
  echo "$@" >&2
  exit 1
}

set_environment() {
  # a.s. used to wait until solr is up and running
  export solr_host=${solr_host}
  export solr_port=${solr_port}

  export CKAN_SITE_ID=${CKAN_SITE_ID}
  export CKAN_SITE_URL=${CKAN_SITE_URL}
  export CKAN_SQLALCHEMY_URL=${CKAN_SQLALCHEMY_URL}
  export CKAN_SOLR_URL=${CKAN_SOLR_URL}
  export CKAN_REDIS_URL=${CKAN_REDIS_URL}
  export CKAN_STORAGE_PATH=/var/lib/ckan
  export CKAN_DATAPUSHER_URL=${CKAN_DATAPUSHER_URL}
  export CKAN_DATASTORE_WRITE_URL=${CKAN_DATASTORE_WRITE_URL}
  export CKAN_DATASTORE_READ_URL=${CKAN_DATASTORE_READ_URL}
  export CKAN_SMTP_SERVER=${CKAN_SMTP_SERVER}
  export CKAN_SMTP_STARTTLS=${CKAN_SMTP_STARTTLS}
  export CKAN_SMTP_USER=${CKAN_SMTP_USER}
  export CKAN_SMTP_PASSWORD=${CKAN_SMTP_PASSWORD}
  export CKAN_SMTP_MAIL_FROM=${CKAN_SMTP_MAIL_FROM}
  export CKAN_MAX_UPLOAD_SIZE_MB=${CKAN_MAX_UPLOAD_SIZE_MB}

  export AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
  export AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
  export AWS_REGION=${AWS_REGION}
  export AWS_CKAN_GROUP=${AWS_CKAN_GROUP}
  export AWS_CKAN_STREAM=${AWS_CKAN_STREAM}

  export oce_email_distribution_group=${oce_email_distribution_group}
}

write_config() {
  ckan-paster make-config --no-interactive ckan "$CONFIG"
}

# Wait for PostgreSQL
# a.s. good when using docker, not necessary with RDS
# a.s. while ! pg_isready -h db -U postgres; do
 while ! pg_isready -h db -U ckan; do
   sleep 1;
 done

# a.s.
# Apache Solr connection details
# solr_host="solr"
# solr_port="8983"
until curl -f "http://${solr_host}:${solr_port}"; do
  # until curl -f "$CKAN_SOLR_URL"; do
  echo >&2 "Solr is not ready - sleeping"
  sleep 1
done

# If we don't already have a config file, bootstrap
if [ ! -e "$CONFIG" ]; then
  write_config
fi

# m.m. - replace Google Analytics ID
sed -i "s/GAID/$GAID/g" "${CKAN_CONFIG}/production.ini"

# Get or create CKAN_SQLALCHEMY_URL
if [ -z "$CKAN_SQLALCHEMY_URL" ]; then
  abort "ERROR: no CKAN_SQLALCHEMY_URL specified in docker-compose.yml"
fi

if [ -z "$CKAN_SOLR_URL" ]; then
  abort "ERROR: no CKAN_SOLR_URL specified in docker-compose.yml"
fi

if [ -z "$CKAN_REDIS_URL" ]; then
  abort "ERROR: no CKAN_REDIS_URL specified in docker-compose.yml"
fi

if [ -z "$CKAN_DATAPUSHER_URL" ]; then
  abort "ERROR: no CKAN_DATAPUSHER_URL specified in docker-compose.yml"
fi

set_environment
ckan-paster --plugin=ckan db init -c "${CKAN_CONFIG}/production.ini"


exec "$@"
