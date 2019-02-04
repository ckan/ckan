#!/bin/sh

#Create softlinks for CKAN installation
#Fore the repo

echo "*** Running setUpCKAN ***"

mkdir -p ~/ckan/lib && sudo ln -s ~/ckan/lib /usr/lib/ckan && mkdir -p ~/ckan/etc && sudo ln -s ~/ckan/etc /etc/ckan

sudo mkdir -p /usr/lib/ckan/default && sudo chown `whoami` /usr/lib/ckan/default && virtualenv --no-site-packages /usr/lib/ckan/default && . /usr/lib/ckan/default/bin/activate

pip install setuptools==36.1 && pip install -e 'git+https://github.com/ckan/ckan.git@ckan-2.8.1#egg=ckan' && pip install -r /usr/lib/ckan/default/src/ckan/requirements.txt

deactivate
. /usr/lib/ckan/default/bin/activate
