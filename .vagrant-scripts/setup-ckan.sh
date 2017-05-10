#!/bin/bash

## Install CKAN for the current user

set -e

pip install --user virtualenv virtualenvwrapper

source "$HOME"/.local/bin/virtualenvwrapper.sh
export PATH="${HOME}/.local/bin/:${PATH}"

echo 'source ~/.local/bin/virtualenvwrapper.sh' >> ~/.bashrc
echo 'export PATH="${HOME}/.local/bin/:${PATH}"' >> ~/.bashrc

set +e
mkvirtualenv ckan
workon ckan
set -e

## Install ckan + requirements
cd /vagrant/
pip install -r requirements.txt
#pip install -r dev-requirements.txt
python setup.py develop


## Create configuration file
mkdir -p "$VIRTUAL_ENV"/etc/ckan
CONF_FILE="$VIRTUAL_ENV"/etc/ckan/development.ini
paster --plugin=ckan make-config --no-install ckan "$CONF_FILE"

SA_URL="postgresql://ckan:pass@localhost/ckan"
SA_DS_RW_URL="postgresql://ckan:pass@localhost/ckan_datastore"
SA_DS_RO_URL="postgresql://ckan_ro:pass@localhost/ckan_datastore"

## Hackish way to change configuration options..
sed -f - -i $CONF_FILE <<EOF
s%^#*\s*sqlalchemy.url\s*=.*\$%sqlalchemy.url = $SA_URL%
s%^#*\s*ckan.datastore.write_url\s*=.*\$%ckan.datastore.write_url = $SA_DS_RW_URL%
s%^#*\s*ckan.datastore.read_url\s*=.*\$%ckan.datastore.read_url = $SA_DS_RO_URL%
s%^#*\s*solr_url\s*=.*\$%solr_url = http://localhost:8983/solr%
EOF

## Copy other configuration files
cp -t "$VIRTUAL_ENV"/etc/ckan/ /vagrant/who.ini


## Installation completed message
cat <<EOF
CKAN installation complete
--------------------------

What to do now:

* Check that the configuration file is OK.
  File: $CONF_FILE

* Initialize the database::

    paster --plugin=ckan db --config=$CONF_FILE init

* Rebuild the search index (?)::

    paster --plugin=ckan search-index --config=$CONF_FILE rebuild

* Run paster server to serve the thing::

    paster --plugin=ckan serve $CONF_FILE

* Offer me a beer :)

EOF
