#!/usr/bin/env bash

set -e;

sudo -u postgres psql <<EOL
 CREATE DATABASE ckan_test OWNER ckan_default;
 GRANT ALL PRIVILEGES ON DATABASE "ckan_test" to ckan_default;
EOL
