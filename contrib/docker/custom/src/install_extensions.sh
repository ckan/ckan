#!/bin/sh
set -e

###
# install_extensions.sh
#
# add the instructions to install your extensions here
# this file is only executed once when the container is first started
# you will have to rebuild and re-run the container to execute it
#
# The reason why the extensions are not installed in the Dockerfile is that
# (at least on my setup) it won't save the changes. Feel free to try and prove me wrong
# on the plus side that means it's easy to customise & run custom commands if needed
###

# archiver
. $CKAN_HOME && \
  $CKAN_HOME/bin/pip install \
    -e git+http://github.com/ckan/ckanext-archiver.git#egg=ckanext-archiver && \
  $CKAN_HOME/bin/pip install \
    -r $CKAN_HOME/src/ckanext-archiver/pip-requirements.txt

# spatial
. $CKAN_HOME && \
  $CKAN_HOME/bin/pip install \
    -e git+https://github.com/ckan/ckanext-spatial.git#egg=ckanext-spatial && \
  $CKAN_HOME/bin/pip install \
    -r $CKAN_HOME/src/ckanext-spatial/pip-requirements.txt

# harvest
. $CKAN_HOME && \
  $CKAN_HOME/bin/pip install \
    -e git+https://github.com/ckan/ckanext-harvest.git#egg=ckanext-harvest && \
  $CKAN_HOME/bin/pip install \
    -r $CKAN_HOME/src/ckanext-harvest/pip-requirements.txt

# searchhistory
. $CKAN_HOME && \
  $CKAN_HOME/bin/pip install \
    -e git+https://github.com/ckan/ckanext-searchhistory.git#egg=ckanext-searchhistory

# dcat
. $CKAN_HOME && \
  $CKAN_HOME/bin/pip install \
    -e git+https://github.com/ckan/ckanext-dcat.git#egg=ckanext-dcat
