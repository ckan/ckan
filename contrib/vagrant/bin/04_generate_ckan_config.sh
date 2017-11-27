#!/usr/bin/env bash

set -e;

sudo mkdir -p /etc/ckan/default;
sudo chown -R `whoami` /etc/ckan/;

. /usr/lib/ckan/default/bin/activate;
/usr/lib/ckan/default/bin/paster make-config ckan /etc/ckan/default/development.ini;

sed -E -i 's#^sqlalchemy.url(.+?)$#sqlalchemy.url = postgresql://ckan_default:pass@localhost/ckan_default#g' /etc/ckan/default/development.ini;
sed -E -i 's#^ckan.site_id(.+?)$#ckan.site_id = default#g' /etc/ckan/default/development.ini;
sed -E -i 's#^ckan.site_url(.+?)$#ckan.site_url = http://localhost#g' /etc/ckan/default/development.ini;
