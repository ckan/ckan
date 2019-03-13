# Setup

#### Install Docker

```
sudo apt-get update
sudo apt-get install docker
```

#### Install latest docker-compose

For Ubuntu 18.04+

```
sudo apt-get update
sudo apt-get install docker-compose
```

or if your version of ubuntu does not support a new enough docker-compose you can pull the latest from github. Make sure to remove the apt version first.

```
sudo curl -L "https://github.com/docker/compose/releases/download/1.22.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
docker-compose --version
```

#### Install Apache

If proxying docker behind Apache (recommended) you will need to have that installed as well. nginx will also work but is not covered in this guide.

```
sudo apt-get update
sudo apt-get install docker-compose
```

#### Add Apache modules

We will use apache to proxy our docker containers so will need a few modules to make that work

```
sudo a2enmod ssl
sudo a2enmod proxy
sudo a2enmod proxy_http
sudo service apache2 restart
```

---

#### Download CKAN git repo

Clone with ssh key

```
cd ~
git clone -b cioos git@github.com:canadian-ioos/ckan.git
cd ckan
git checkout cioos
```

Clone with https

```
cd ~
git clone -b cioos https://github.com/canadian-ioos/ckan.git
cd ckan
git checkout cioos
```

add submodules

```
cd ~/ckan
git submodule init
git submodule update
```

---

#### Create config files

create environment file and populate with appropriate values

```
cd ~/ckan/contrib/docker/
cp .env.template .env
nano .env
```

create ckan config files for later import into ckan

```
cd ~/ckan/contrib/docker/
cp production_non_root_url.ini production.ini
cp who_non_root_url.ini who.ini
```

or

```
cd ~/ckan/contrib/docker/
cp production_root_url.ini production.ini
cp who_root_url.ini who.ini
```

copy pyCSW config file and update the database password. This ist he same password enetered in your .env file

```
cd ~/ckan/contrib/docker/pycsw
cp pycsw.cfg.template pycsw.cfg
nano pycsw.cfg
```

---

#### Build CKAN

Change to ckan docker config folder

```
  cd ~/ckan/contrib/docker
```

Build containers

```
sudo docker-compose up -d --build
```

if this fails try manually pulling the images first e.g.:

```
 docker pull --disable-content-trust clementmouchet/datapusher
 docker pull --disable-content-trust redis:latest
```

Sometimes the containers start in the wrong order. This often results in strange sql errors in the db logs. If this happens you can manually start the containers by first building then using docker-compose up

```
sudo docker-compose build
sudo docker-compose up db
sudo docker-compose up solr redis
sudo docker-compose up ckan
sudo docker-compose up datapusher
sudo docker-compose up ckan_gather_harvester ckan_fetch_harvester ckan_run_harvester
```

if you need to change the production.ini in the repo and rebuild then you may need to delete the volume first. volume does not update during dockerfile run if it already exists.

```
docker-compose down
docker volume rm docker_ckan_config
```

update ckan/contrib/docker/production.ini

```
  export VOL_CKAN_CONFIG=`sudo docker volume inspect docker_ckan_config | jq -r -c '.[] | .Mountpoint'`
  sudo nano $VOL_CKAN_CONFIG/production.ini
```

#### Setup Apache proxy

add the following to your sites configs

```
    # CKAN
		<location /ckan>
  	    ProxyPass http://localhost:5000/
  	    ProxyPassReverse http://localhost:5000/
   	</location>

    # pycsw
     <location /ckan/csw>
         ProxyPass http://localhost:8000/pycsw/csw.js
         ProxyPassReverse http://localhost:8000/pycsw/csw.js
    </location>
```

or

```
    # CKAN
    <location />
        ProxyPass http://localhost:5000/
        ProxyPassReverse http://localhost:5000/
    </location>

    # pycsw
    <location /csw>
        ProxyPass http://localhost:8000/pycsw/csw.js
        ProxyPassReverse http://localhost:8000/pycsw/csw.js
    </location>

```

If you use rewrite rules to redirect none ssl traffic to https and you are using a non-root install, such as /ckan, then you will likely need to add a no escape flag to your rewrite rules. something like the following should work, note the NE.

```
  RewriteEngine on
  ReWriteCond %{SERVER_PORT} !^443$
  RewriteRule ^/(.*) https://%{HTTP_HOST}/$1 [NC,R,L,NE]
```

restart apache

```
  sudo service apache2 restart
```

Create ckan admin user

```
sudo docker exec -it ckan /usr/local/bin/ckan-paster --plugin=ckan sysadmin -c /etc/ckan/production.ini add admin
```

#### Configure admin settings

in the admin page of ckan set style to default and homepage to CIOOS to get the full affect of the cioos_theme extention

---

## Setup Harvesters

Add Organization
URL: `https://localhost/ckan/organization`

Add Harvester
URL: `https://localhost/ckan/harvest`

The settings for harvesters are fairly straightforward. The one exception is the configuration section. Some example configs are listed below.

#### CSW (geonetwork)

```
{
 "default_tags": ["geonetwork"],
 "default_extras": {"encoding":"utf8",
"h_source_id": "{harvest_source_id}",
"h_source_url":"https://hecate.hakai.org/geonetwork/srv/eng/catalog.search#/metadata/",
"h_source_title": "{harvest_source_title}",
"h_job_id":"{harvest_job_id}",
"h_object_id":"{harvest_object_id}"},
  "override_extras": true,
  "clean_tags": true,
"harvest_iso_categories": true,
"group_mapping": {
          "farming": "farming",
          "utilitiesCommunication": "boundaries",
          "transportation": "boundaries",
          "inlandWaters": "inlandwaters",
          "geoscientificInformation": "geoscientificinformation",
          "environment": "environment",
          "climatologyMeteorologyAtmosphere": "climatologymeteorologyatmosphere",
          "planningCadastre": "boundaries",
          "imageryBaseMapsEarthCover": "imagerybasemapsearthcover",
          "elevation": "elevation",
          "boundaries": "boundaries",
          "structure": "boundaries",
          "location": "boundaries",
          "economy": "economy",
          "society": "economy",
          "biota": "biota",
          "intelligenceMilitary": "boundaries",
          "oceans": "oceans",
          "health": "health"
     }
}
```

#### WAF (ERDDAP)

```
{
 "default_tags": ["erddap"],
 "default_extras": {"encoding":"utf8",
    "guid_suffix":"_iso19115.xml",
    "h_source_id": "{harvest_source_id}",
    "h_source_url": "{harvest_source_url}",
    "h_source_title": "{harvest_source_title}",
    "h_job_id": "{harvest_job_id}",
    "h_object_id": "{harvest_object_id}"
},
 "override_extras": false,
 "clean_tags": true,
 "validator_profiles": ["iso19139ngdc"],
"harvest_iso_categories": true,
"group_mapping": {
          "farming": "farming",
          "utilitiesCommunication": "boundaries",
          "transportation": "boundaries",
          "inlandWaters": "inlandwaters",
          "geoscientificInformation": "geoscientificinformation",
          "environment": "environment",
          "climatologyMeteorologyAtmosphere": "climatologymeteorologyatmosphere",
          "planningCadastre": "boundaries",
          "imageryBaseMapsEarthCover": "imagerybasemapsearthcover",
          "elevation": "elevation",
          "boundaries": "boundaries",
          "structure": "boundaries",
          "location": "boundaries",
          "economy": "economy",
          "society": "economy",
          "biota": "biota",
          "intelligenceMilitary": "boundaries",
          "oceans": "oceans",
          "health": "health"
     }
}
```

#### CKAN

```
{
 "default_tags": [{"name": "ckan"}, {"name": "production"}],
 "default_extras": {"encoding":"utf8",
     "h_source_id": "{harvest_source_id}",
     "h_source_url":"{harvest_source_url}",
     "h_source_title": "{harvest_source_title}",
     "h_job_id":"{harvest_job_id}",
     "h_object_id":"{harvest_object_id}"},
  "clean_tags": true,
 "remote_groups": "create",
 "remote_orgs": "create",
 "use_default_schema": true,
 "force_package_type": "dataset"
}
```

---

#### Finish setting up pyCSW

create pycsw database in existing pg container and install postgis

```
sudo docker exec -i db psql -U ckan
CREATE DATABASE pycsw OWNER ckan ENCODING 'utf-8';
\c pycsw
CREATE EXTENSION postgis;
\q
```

setup pycsw database tables.

```
sudo docker exec -it ckan /usr/local/bin/ckan-paster --plugin=ckanext-spatial ckan-pycsw setup -p /usr/lib/ckan/venv/src/pycsw/default.cfg
```

start pycsw container

```
sudo docker-compose up -d pycsw
```

#### test GetCapabilities

<https://localhost/ckan/csw/?service=CSW&version=2.0.2&request=GetCapabilities>

or

<https://localhost/csw/?service=CSW&version=2.0.2&request=GetCapabilities>

#### Useful pycsw commands

access pycsw-admin

```
sudo docker exec -ti pycsw pycsw-admin.py -h
```

Load the CKAN datasets into pycsw

```
sudo docker exec -it ckan /usr/local/bin/ckan-paster --plugin=ckanext-spatial ckan-pycsw load -p /usr/lib/ckan/venv/src/pycsw/default.cfg -u http://localhost:5000
```

ckan-pycsw commands

```
sudo docker exec -it ckan /usr/local/bin/ckan-paster --plugin=ckanext-spatial ckan-pycsw --help
sudo docker exec -it ckan /usr/local/bin/ckan-paster --plugin=ckanext-spatial ckan-pycsw setup -p /usr/lib/ckan/venv/src/pycsw/default.cfg
sudo docker exec -it ckan /usr/local/bin/ckan-paster --plugin=ckanext-spatial ckan-pycsw set_keywords -p /usr/lib/ckan/venv/src/pycsw/default.cfg -u http://localhost:5000
sudo docker exec -it ckan /usr/local/bin/ckan-paster --plugin=ckanext-spatial ckan-pycsw load -p /usr/lib/ckan/venv/src/pycsw/default.cfg -u http://localhost:5000
sudo docker exec -it ckan /usr/local/bin/ckan-paster --plugin=ckanext-spatial ckan-pycsw clear -p /usr/lib/ckan/venv/src/pycsw/default.cfg
```

errors while pycsw loading
if you get "Error:Cannot commit to repository" and "HINT: Values larger than 1/3 of a buffer page cannot be indexed." you are likely loading abstracts or other fields that are to big to be indexed in the database. You can either remove the index or switch to an index using the md5 encoded version of the value.

connect to db

```
sudo docker exec -i db psql -U ckan
\c pycsw
```

remove index

```
DROP INDEX ix_records_abstract;
```

add md5 index

```
CREATE INDEX ix_records_abstract ON records((md5(abstract)));
```

---

# Troubleshooting

Is ckan running? Check container is running and view logs

```
  sudo docker ps | grep ckan
  sudo docker-compose logs -f ckan
```

if container isn’t running its probably because the db didn’t build in time. restart…

```
  sudo docker-compose restart ckan
```

Connect to container as root to debug

```
  sudo docker exec -u root -it ckan /bin/bash -c "export TERM=xterm; exec bash"
```

If you rebuilt the ckan container and no records are showing up, you need to reindex the records.

```
sudo docker exec -it ckan //usr/local/bin/ckan-paster --plugin=ckan search-index rebuild --config=/etc/ckan/production.ini
```

you have done several builds of ckan and now you are running out of hard drive space? With ckan running you can clean up docker images, containers, etc.

```
  docker system prune -a
```

or remove only the images you want with

```
	docker image ls
	docker rmi [image name]
```

#### When creating organizations or updating admin config settings you get a 500 Internal Server Error

This can be caused by ckan not having permissions to write to the internal storage of the ckan container. This should be setup during the build process. You can debug this by setting debug = true in the production.ini file. No error messages will be reported in the ckan logs for this issue without turning on debug.

To fix chage the owner of the ckan storage folder and its children

```
  sudo docker exec -u root -it ckan /bin/bash -c "export TERM=xterm; exec bash"
  chown -R ckan:ckan $CKAN_HOME $CKAN_VENV $CKAN_CONFIG $CKAN_STORAGE_PATH
  exit
```

#### Build fails with 'Temporary failure resolving...' errors

Likely the issue is that docker is passing the wrong DNS lookup addresses to the
containers on build. See issue this issue on stack overflow https://stackoverflow.com/a/45644890
for a solution.

---

# Update CKAN and its extensions

enable volume environment variables to make accessing the volumes easier

```
export VOL_CKAN_HOME=`sudo docker volume inspect docker_ckan_home | jq -r -c '.[] | .Mountpoint'`
export VOL_CKAN_CONFIG=`sudo docker volume inspect docker_ckan_config | jq -r -c '.[] | .Mountpoint'`
export VOL_CKAN_STORAGE=`sudo docker volume inspect docker_ckan_storage | jq -r -c '.[] | .Mountpoint'`
echo $VOL_CKAN_HOME
echo $VOL_CKAN_CONFIG
echo $VOL_CKAN_STORAGE
```

update submodules

```
cd ~/ckan
git pull
git submodule update
```

copy updated extension code to the volumes

```
cd ~/ckan/contrib/docker
sudo cp -r src/ckanext-cioos_theme/ $VOL_CKAN_HOME/venv/src/
sudo cp -r src/ckanext-harvest/ $VOL_CKAN_HOME/venv/src/
sudo cp -r src/ckanext-spatial/ $VOL_CKAN_HOME/venv/src/
sudo cp -r src/pycsw/ $VOL_CKAN_HOME/venv/src/
sudo cp -r src/ckanext-doi/ $VOL_CKAN_HOME/venv/src/
sudo cp -r src/ckanext-scheming/ $VOL_CKAN_HOME/venv/src/
sudo cp -r src/ckanext-package_converter/ $VOL_CKAN_HOME/venv/src/
```

update permissions

```
sudo chown 900:900 -R $VOL_CKAN_HOME/venv/src/
```

restart the container affected by the change. If changing html files you may not need to restart anything

```
cd ~/ckan/contrib/docker
sudo docker-compose restart ckan
sudo docker-compose restart ckan_run_harvester ckan_fetch_harvester ckan_gather_harvester
```
