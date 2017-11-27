#!/usr/bin/env bash
set -e;

sudo -u postgres psql -l;

sudo -u postgres psql <<EOL
 CREATE USER ckan_default password 'pass' SUPERUSER CREATEDB;
 CREATE DATABASE ckan_default OWNER ckan_default;
 GRANT ALL PRIVILEGES ON DATABASE "ckan_default" to ckan_default;
EOL
