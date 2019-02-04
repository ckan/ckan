#!/bin/sh

echo "**** running startCKAN ****"

cd /usr/lib/ckan/default/src/ckan
paster serve /etc/ckan/default/development.ini