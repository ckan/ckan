#!/usr/bin/env bash
# Implements of http://docs.ckan.org/en/ckan-2.7.2/maintaining/datastore.html
set -e;

# Enable the plugin
sudo sed -i -E 's#ckan.plugins = (.+?)$#ckan.plugins = stats text_view image_view recline_view datastore#g' /etc/ckan/default/development.ini;

# Create users and databases
sudo -u postgres psql <<EOL
 CREATE USER datastore_default password 'pass';

 CREATE DATABASE datastore_default OWNER ckan_default;
 CREATE DATABASE datastore_test OWNER ckan_default;
EOL
# GRANT ALL PRIVILEGES ON DATABASE "datastore_default" to ckan_default;
# GRANT SELECT ON DATABASE "datastore_test" to ckan_default;

# Set URLs
sudo sed -E -i 's%#*ckan.datastore.write_url(.+?)$%ckan.datastore.write_url = postgresql://ckan_default:pass@localhost/datastore_default%g' /etc/ckan/default/development.ini;
sudo sed -E -i 's%#*ckan.datastore.read_url(.+?)$%ckan.datastore.read_url = postgresql://datastore_default:pass@localhost/datastore_default%g' /etc/ckan/default/development.ini;

# Set permissions

. /usr/lib/ckan/default/bin/activate;

paster --plugin=ckan datastore set-permissions -c /etc/ckan/default/development.ini | sudo -u postgres psql --set ON_ERROR_STOP=1
