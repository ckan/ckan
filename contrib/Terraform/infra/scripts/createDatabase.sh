#!/bin/sh

echo "*** Running createDatabase ***"

cd /usr/lib/ckan/default/src/ckan
. /usr/lib/ckan/default/bin/activate
paster db init -c /etc/ckan/default/development.ini