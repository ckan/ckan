Notes on the new CKAN Docker
solr Dockerfile has this line ENV CKAN_VERSION dev-v2.8 (what should this be for the new version?)

Build a new CKAN image (using alpine as base, Python3 and CKAN 2.9)
# docker image build -t ckan-base-NEW .
docker build -t kowhai/ckan-base:2.9 -f ckan/2.9/Dockerfile .

postgresql version needs to increase to 9.5 (at least)
Look at where sensitive data can be obfuscated

TO DO
1. Add Dev Mode
2. Add patches directory

Notes

-Development Mode-

docker-compose -f docker-compose.dev.yml build
docker-compose -f docker-compose.dev.yml up

Dockerfile.dev: this is based on openknowledge/ckan-dev (with the Dockerfile on the /ckan-dev/<version> folder), wich extends openknowledge/ckan-base to include:

Any extension cloned on the src folder will be installed in the CKAN container when booting up Docker Compose (docker-compose up). 
This includes installing any requirements listed in a requirements.txt (or pip-requirements.txt) file and running python setup.py develop.
The CKAN image used will development requirements needed to run the tests.
CKAN will be started running on the ckan development server, with the --reload option to watch changes in the extension files.
Make sure to add the local plugins to the CKAN__PLUGINS env var in the .env file.

Patches
When building your project specific CKAN images (the ones defined in the ckan/ folder), you can apply patches to CKAN core or any of the built extensions. To do so create a folder inside ckan/patches with the name of the package to patch (ie ckan or ckanext-??). Inside you can place patch files that will be applied when building the images. The patches will be applied in alphabetical order, so you can prefix them sequentially if necessary.

For instance, check the following example image folder:

ckan
├── patches
│   ├── ckan
│   │   ├── 01_datasets_per_page.patch
│   │   ├── 02_groups_per_page.patch
│   │   ├── 03_or_filters.patch
│   └── ckanext-harvest
│       └── 01_resubmit_objects.patch
├── Dockerfile
└── Dockerfile.dev