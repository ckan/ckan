#!/bin/bash

# This is a script which uses BuildKit 0.2.0 to automatically package CKAN and
# its dependencies for use as Debian packages on Ubuntu 10.04.
#
# See the BuildKit documentation or look at the help to see what these commands
# do. eg:
#
#     buildkit --help
#
# The licenses and solrpy packages have to be built separately from the others
# because they are slighlty non-standard. All other CKAN dependencies are
# automatically handled by the --deps option to the CKAN build command.
# 
# Over time, as CKAN and its dependencies follow conventions more closely the
# edge cases handled by this script should go away and the build should become
# simpler.

CKAN_PACKAGE_VERSION=08
DEPS_PACKAGE_VERSION=05
CKAN_PATH=/home/james/Documents/Work/OKFN/code/pyenv/src/ckan
BUILDKIT_REPO_PATH="/var/lib/buildkit/repo/ckan-1.5"
PIP_DOWNLOAD_CACHE=${CKAN_PATH}/build/env/cache
EMAIL=packaging@okfn.org
NAME="James Gardner"

# Clean the build environment
echo "Cleaning the environment ..."
rm -r ${CKAN_PATH}/dist/
rm -rf ${CKAN_PATH}/build/env/src
mkdir -p ${CKAN_PATH}/dist/buildkit
echo "done."

echo "Buildling the packages ..."
# Create the python-ckan debian package
buildkit pkg python -p $CKAN_PACKAGE_VERSION --delete "solrpy" --distro-dep "python-solr" --delete "licenses" --distro-dep "python-licenses" --delete "repoze.who-friendlyform" --rename "repoze.who.plugins.openid -> repoze.who-plugins" --rename "babel -> pybabel" --author-email="$EMAIL" --author-name="$NAME" --packager-email="$EMAIL" --packager-name="$NAME" --deps --exclude=test/generate_package --conflict-module "sqlalchemy-migrate -> migrate" --conflict-module "sqlalchemy -> lib/sqlalchemy" --debian-dir --url http://ckan.org ${CKAN_PATH}

# Creates the ckan debian package (of which python-ckan is a dependency)
buildkit pkg nonpython -p $CKAN_PACKAGE_VERSION --deb --output-dir ${CKAN_PATH}/dist/buildkit ${CKAN_PATH}/ckan_deb

# Build python-solr
${CKAN_PATH}/build/buildkit/env/bin/pip install --download-cache ${CKAN_PATH}/build/buildkit/env/cache --no-install --upgrade "solrpy==0.9.4"
mv ${CKAN_PATH}/build/buildkit/env/build/solrpy ${CKAN_PATH}/build/buildkit/env/build/solr
# We need to rename the package here
sed -e "s,solrpy,solr," -i ${CKAN_PATH}/build/buildkit/env/build/solr/setup.py
# We need to specify an author explicitly since it is missing we'll use the CKAN one
buildkit pkg python -p $DEPS_PACKAGE_VERSION --author-email="$EMAIL" --author-name="$NAME" --packager-email="$EMAIL" --packager-name="$NAME" --debian-dir ${CKAN_PATH}/build/buildkit/env/build/solr/
cp ${CKAN_PATH}/build/buildkit/env/build/solr/dist/buildkit/*.deb ${CKAN_PATH}/dist/buildkit/

# Build python-licenses
${CKAN_PATH}/build/buildkit/env/bin/pip install --download-cache ${CKAN_PATH}/build/buildkit/env/cache --no-install --upgrade "licenses==0.6.1" 
buildkit pkg python --deb -p $DEPS_PACKAGE_VERSION --author-email="$EMAIL" --author-name="$NAME" --packager-email="$EMAIL" --packager-name="$NAME" ${CKAN_PATH}/build/buildkit/env/build/licenses
cp ${CKAN_PATH}/build/buildkit/env/build/licenses/dist/buildkit/*.deb ${CKAN_PATH}/dist/buildkit/
echo "done."

# Add the .debs to the repository and the export the latest files for upload
echo "Adding the packages to the $BUILDKIT_REPO_PATH repo ..."
sudo -u buildkit buildkit repo remove -a $BUILDKIT_REPO_PATH
sudo -u buildkit buildkit repo add $BUILDKIT_REPO_PATH ${CKAN_PATH}/dist/buildkit/*.deb
echo "done."

