Notes on the new CKAN Docker
solr Dockerfile has this line ENV CKAN_VERSION dev-v2.8 (what should this be for the new version?)

Build a new CKAN image (using alpine as base, Python3 and CKAN 2.9)
# docker image build -t ckan-base-NEW .
docker build -t kowhai/ckan-base:2.9 -f ckan/2.9/Dockerfile .

postgresql version needs to increase to 9.5 (at least)
Look at where sensitive data can be obfuscated