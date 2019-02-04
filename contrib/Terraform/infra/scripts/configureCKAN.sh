#!/bin/sh

sudo mkdir -p /etc/ckan/default
sudo chown -R `whoami` /etc/ckan/
sudo chown -R `whoami` ~/ckan/etc

. /usr/lib/ckan/default/bin/activate
paster make-config ckan /etc/ckan/default/development.ini

cp /home/ubuntu/resources/development.ini /etc/ckan/default/development.ini
cat /etc/ckan/default/development.ini