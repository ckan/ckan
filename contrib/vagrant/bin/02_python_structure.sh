#!/usr/bin/env bash
set -e;
# Make virtualenv
sudo mkdir -p /usr/lib/ckan/default
sudo chown -R `whoami` /usr/lib/ckan/default
virtualenv --no-site-packages /usr/lib/ckan/default
. /usr/lib/ckan/default/bin/activate;

# Install required setuptools version
pip install -r /vagrant/requirement-setuptools.txt
# Install CKAN
pip install -e /vagrant;
# Install CKAN dependencies
pip install -r /vagrant/requirements.txt
