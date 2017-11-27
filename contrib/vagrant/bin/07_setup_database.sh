#!/usr/bin/env bash

set -e;

. /usr/lib/ckan/default/bin/activate;

cd /vagrant;
paster db init -c /etc/ckan/default/development.ini;
