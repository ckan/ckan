#!/usr/bin/env bash

set -e;

sudo cp -r /usr/share/solr/ /etc/solr/ckan
curl 'http://localhost:8983/solr/admin/cores?action=CREATE&name=ckan&instanceDir=/etc/solr/ckan'
sudo sed -i 's#solr_url(.+?)$#http://127.0.0.1:8983/solr/ckan#g' /etc/ckan/default/development.ini;
