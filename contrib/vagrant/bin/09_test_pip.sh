#!/usr/bin/env bash

set -e;

. /usr/lib/ckan/default/bin/activate;
/usr/lib/ckan/default/bin/pip install -r /vagrant/dev-requirements.txt
