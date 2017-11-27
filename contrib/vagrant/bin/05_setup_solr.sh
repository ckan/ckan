#!/usr/bin/env bash

set -e;

# Update SOLR startup script
sudo sed -E -i 's@#*NO_START(.+?)$@NO_START=0@g' /etc/default/jetty8;
sudo sed -E -i 's@#*JETTY_HOST(.+?)$@JETTY_HOST=0.0.0.0@g' /etc/default/jetty8;
sudo sed -E -i 's@#*JETTY_PORT(.+?)$@JETTY_PORT=8983@g' /etc/default/jetty8;

# Restart Jetty8
sudo service jetty8 restart;

# Replace the default schema.xml file with a symlink to the CKAN schema file
sudo mv /etc/solr/conf/schema.xml /etc/solr/conf/schema.xml.bak;
sudo ln -s /vagrant/ckan/config/solr/schema.xml /etc/solr/conf/schema.xml;
sudo service jetty8 restart;
sed -i 's#solr_url(.+?)$#http://127.0.0.1:8983/solr#g' /etc/ckan/default/development.ini;
