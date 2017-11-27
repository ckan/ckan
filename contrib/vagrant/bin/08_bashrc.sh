#!/usr/bin/env bash

set +e;

cat <<EOL >> /home/vagrant/.bashrc
export CKAN_INI=/etc/ckan/default/development.ini
. /usr/lib/ckan/default/bin/activate;
cd /vagrant;
EOL
