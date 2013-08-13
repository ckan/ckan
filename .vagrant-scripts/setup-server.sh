#!/bin/bash

##====================================================================
## Script to prepare the machine for running a CKAN development
## environment
##====================================================================

## Terminate immediately if any command fails
set -e

## Install dependencies
apt-get update -y -qq
xargs apt-get install -y -qq <<EOF
python-dev

solr-jetty
openjdk-6-jdk

postgresql-9.1
postgresql-contrib-9.1
postgresql-server-dev-9.1
EOF


##--------------------------------------------------------------------
## Setup PostgreSQL users/databases

sudo -u postgres psql <<EOF
CREATE USER ckan WITH PASSWORD 'pass';
CREATE USER ckan_ro WITH PASSWORD 'pass';

CREATE DATABASE ckan
    WITH OWNER ckan
    ENCODING = 'UTF8'
    LC_CTYPE = 'en_US.utf8'
    LC_COLLATE = 'en_US.utf8'
    TEMPLATE template0;

CREATE DATABASE ckan_datastore
    WITH OWNER ckan
    ENCODING = 'UTF8'
    LC_CTYPE = 'en_US.utf8'
    LC_COLLATE = 'en_US.utf8'
    TEMPLATE template0;
EOF


##--------------------------------------------------------------------
## Configure Solr/Jetty

if [ -z "$JAVA_HOME" ]; then
    ## todo: any better way to do this?
    JAVA_HOME=/usr/lib/jvm/java-6-openjdk-amd64/
fi

cat > /etc/default/jetty <<EOF
NO_START=0
JETTY_HOST=127.0.0.1
JETTY_PORT=8983
JAVA_HOME=$JAVA_HOME
EOF

## Copy Solr schema over, from the CKAN directory
cp /vagrant/ckan/config/solr/schema-2.0.xml /etc/solr/conf/schema.xml

echo "Configured Jetty. Restarting..."
service jetty restart


##--------------------------------------------------------------------
## Install Python dependencies

apt-get install -y -qq python-dev python-pip git

## Install CKAN, as the "vagrant" user
cd /home/vagrant/
su - vagrant -c '/bin/bash /vagrant/.vagrant-scripts/setup-ckan.sh'
