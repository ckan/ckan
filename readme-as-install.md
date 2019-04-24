# Docker Installation

``` shell

~/code/ckan $ git clone git@github.com:marsdd/ckan.git ckan

# follow instructions within to set passwords and other sensitive or user-defined variables.
~/code/ckan $ cp contrib/docker/.env.template contrib/docker/.env

# build docker image
~/code/ckan $ cd contrib/docker

# docker-compose commands are all run inside contrib/docker, where docker-compose.yml and .env are located.

~/code/ckan $ docker-compose up -d --build

# On first runs, the postgres container could need longer to initialize the database cluster than the ckan container will wait for. This time span depends heavily on available system resources. If the CKAN logs show problems connecting to the database, restart the ckan container a few times:

~/code/ckan $ docker-compose restart ckan
~/code/ckan $ docker ps | grep ckan
~/code/ckan $ docker-compose logs -f ckan

# After this step, CKAN should be running at CKAN_SITE_URL.

# There should be five containers running (docker ps):
#   ckan: CKAN with standard extensions
#   db: CKAN’s database, later also running CKAN’s datastore database
#   redis: A pre-built Redis image.
#   solr: A pre-built SolR image set up for CKAN.
#   datapusher: A pre-built CKAN Datapusher image.

# There should be four named Docker volumes (docker volume ls | grep docker). They will be prefixed with the Docker Compose project name (default: docker or value of host environment variable COMPOSE_PROJECT_NAME.)

#   docker_ckan_config: home of production.ini
#   docker_ckan_home: home of ckan venv and source, later also additional CKAN extensions
#   docker_ckan_storage: home of CKAN’s filestore (resource files)
#   docker_pg_data: home of the database files for CKAN’s default and datastore databases

# jq is a lightweight and flexible command-line JSON processor.
brew install jq

# Find the path to a named volume
docker volume inspect docker_ckan_home | jq -c '.[] | .Mountpoint'
# "/var/lib/docker/volumes/docker_ckan_config/_data"

export VOL_CKAN_HOME=`docker volume inspect docker_ckan_home | jq -r -c '.[] | .Mountpoint'`
echo $VOL_CKAN_HOME

export VOL_CKAN_CONFIG=`docker volume inspect docker_ckan_config | jq -r -c '.[] | .Mountpoint'`
echo $VOL_CKAN_CONFIG

export VOL_CKAN_STORAGE=`docker volume inspect docker_ckan_storage | jq -r -c '.[] | .Mountpoint'`
echo $VOL_CKAN_STORAGE

# ### Datastore and datapusher

# To enable the datastore, the datastore database and database users have to be created before enabling the datastore and datapusher settings in the production.ini.

# With running CKAN containers, execute the built-in setup scripts against the db container:
docker exec -it db sh /docker-entrypoint-initdb.d/00_create_datastore.sh
docker exec ckan /usr/local/bin/ckan-paster --plugin=ckan datastore set-permissions -c /etc/ckan/production.ini | docker exec -i db psql -U ckan

# If needed install Postgres in order to get psql:

# remove previous version
brew uninstall --force postgresql

# delete all postgres files
rm -rf /usr/local/var/postgres

# install new postgres
brew install postgres

# install postgis
brew install postgis

# start PostgreSQL server
pg_ctl -D /usr/local/var/postgres start

# create database
initdb /usr/local/var/postgres

# If terminal shows an error
# initdb: directory "/usr/local/var/postgres" exists but is not empty. If you want to create a new database system, either remove or empty the directory "/usr/local/var/postgres" or run initdb with an argument other than "/usr/local/var/postgres".

# remove old database file
rm -r /usr/local/var/postgres

# run the initdb command again
initdb /usr/local/var/postgres

# create a new database
createdb postgis_test

# enable PostGIS
psql postgis_test

# SHELL/BASH ACCESS INTO A CONTAINER
# docker exec -it <container name> bash
docker exec -it ckan bash
docker exec -it ckan /bin/bash -c "export TERM=xterm; exec bash"

# After this step, the datastore database is ready to be enabled in the production.ini.

# Enable datastore and datapusher in production.ini

# Edit the production.ini (note: requires sudo):
# sudo vim $VOL_CKAN_CONFIG/production.ini

# To enable datastore and datapusher, uncomment following code in deployment.ini_tmpl:

ckan.datastore.write_url = postgresql://ckan_default:pass@localhost/datastore_default
ckan.datastore.read_url = postgresql://datastore_default:pass@localhost/datastore_default

and

ckan.plugins = stats text_view image_view recline_view datastore datapusher

ckan.datapusher.formats = csv xls xlsx tsv application/csv application/vnd.ms-excel application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
ckan.datapusher.url = http://127.0.0.1:8800/
ckan.datapusher.assume_task_stale_after = 3600

# restart ckan:
docker-compose restart ckan

# add johndoe user
# pwd johndoetest
docker exec -it ckan /usr/local/bin/ckan-paster --plugin=ckan sysadmin -c /etc/ckan/production.ini add johndoe
# Email address: johndoetest@john.ck
# user: johndoe
# pwd: johndoetest

```

## Server volumes

- Images will be stored in following location:
  - var/lib/ckan/storage/uploads/admin ( ${ckan_storage}/storage/uploads/admin )

## Define environment variables

- ENV CKAN_HOME /usr/lib/ckan
- ENV CKAN_VENV $CKAN_HOME/venv
- ENV CKAN_CONFIG /etc/ckan
- ENV CKAN_STORAGE_PATH=/var/lib/ckan

## Synch upstream fork

```shell
~/code/ckan on master*
⚡ git remote -v
origin git@github.com:marsdd/ckan.git (fetch)
origin git@github.com:marsdd/ckan.git (push)

⚡ git remote add upstream https://github.com/ckan/ckan.git

⚡ git remote -v
origin git@github.com:marsdd/ckan.git (fetch)
origin git@github.com:marsdd/ckan.git (push)
upstream https://github.com/ckan/ckan.git (fetch)
upstreamvhttps://github.com/ckan/ckan.git (push)

⚡ git fetch upstream
```
