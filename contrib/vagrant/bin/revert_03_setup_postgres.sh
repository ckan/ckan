#!/bin/sh

set +e;

sudo -u postgres psql -c 'drop database ckan_default'
sudo -u postgres psql -c 'drop user ckan_default'
