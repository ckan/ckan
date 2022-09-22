#!/bin/sh

# SOLR
mkdir -p /etc/solr/conf/
ln -s ~/ckan/config/solr/schema.xml /etc/solr/conf/schema.xml

# OS Dependencies
apt update
curl -sL https://deb.nodesource.com/setup_10.x | bash -
apt install -y nodejs
apt install -y libgtk2.0-0 libgtk-3-0 libnotify-dev libgconf-2-4 libnss3 libxss1 libasound2 libxtst6 xauth xvfb
npm install
apt install -y postgresql-client

#Python Dependencies
pip install -r requirements.txt
pip install -r dev-requirements.txt
python setup.py develop
pip check
