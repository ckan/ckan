# Setup
### Install Docker
```
sudo apt-get update
sudo apt-get install docker
```

### Install latest docker-compose
```
sudo curl -L "https://github.com/docker/compose/releases/download/1.22.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
docker-compose --version
```
or
```
sudo apt-get update
sudo apt-get install docker-compose
```

---
# Download CKAN git repo

### Clone with ssh key
```
cd ~
git clone -b cioos git@github.com:canadian-ioos/ckan.git
cd ckan
git checkout cioos
```

### Clone with https
```
cd ~
git clone -b cioos https://github.com/canadian-ioos/ckan.git
cd ckan
git checkout cioos
```
### add submodules
```
cd ~/ckan
git submodule init
git submodule update
```
---
# Create config files
create enviroment file and populate with approperit values
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

---
# Build CKAN

Change to ckan docker config folder
```
cd ~/ckan/contrib/docker
```

Currently ckan is configured to run in the ckan sub folder on port 5000 so if accessing if from localhost it would be http:localhost:5000/ckan/
If you wish to host ckan at the domain root aka http://localhost:5000 you will need to modify the config files. See ‘Host CKAN on root path’ for more information.

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
if you need to change the production.ini in the repo and rebuild then you may need to  delete the volume first. volume does not update during dockerfile run if it already exists.
```
docker-compose down
docker volume rm docker_ckan_config
```
update ckan/contrib/docker/production.ini
```
sudo nano $VOL_CKAN_CONFIG/production.ini
```

# Setup Apache proxy
add the following to your sites configs
```
# CKAN
		<location /ckan>
      		    ProxyPass http://localhost:5000/
      		    ProxyPassReverse http://localhost:5000/
   		</location>
```
or

```
# CKAN
		<location />
      		    ProxyPass http://localhost:5000/
      		    ProxyPassReverse http://localhost:5000/
   		</location>
```
If you use rewrite rules to redirect none ssl trafic to https and you are using a non-root install, such as /ckan, then you will likely need to add a no escape flag to your rewite rules. something like the following should work, not the NE.
```
  RewriteEngine on
  ReWriteCond %{SERVER_PORT} !^443$
  RewriteRule ^/(.*) https://%{HTTP_HOST}/$1 [NC,R,L,NE]
```
# Create ckan admin user
```
sudo docker exec -it ckan /usr/local/bin/ckan-paster --plugin=ckan sysadmin -c /etc/ckan/production.ini add admin
```

# Configure admin settings
in the admin page of ckan set style to default and homepage to CIOOS to get the full affect of the cioos_theme extention

---
# Setup Harvesters

### Add Orginization
URL: ```https://localhost/ckan/organization```

### Add Harvester
URL: ```https://localhost/ckan/harvest```

The settings for harvesters are fairly straightforward. The one exception is the configuration section. Some exampe configs are listed below.

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
##### WAF (ERDDAP)
```
{
 "default_tags": ["errdap"],
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
 "default_tags": [{"name": "ckan"}, {"name": "SLGO"}, {"name": "St-Lawrence-Global-Observatory"}, {"name": "production"}],
 "default_extras": {"encoding":"utf8",
     "h_source_id": "{harvest_source_id}",
     "h_source_url":"{harvest_source_url}",
     "h_source_title": "{harvest_source_title}",
     "h_job_id":"{harvest_job_id}",
     "h_object_id":"{harvest_object_id}"},
  "clean_tags": true,
 "remote_groups": "create",
 "remote_orgs": "create"
}
```
---
# Troubleshooting

### Is ckan running?
check container is running and view logs
```
  sudo docker ps | grep ckan
  sudo docker-compose logs -f ckan
```
if container isn’t running its probably because the db didn’t build in time. restart…
```
  sudo docker-compose restart ckan
```

### Connect to container as root to debug
```
  sudo docker exec -u root -it ckan /bin/bash -c "export TERM=xterm; exec bash"
```

### If you rebuilt the ckan container and no records are showing up, you need to reindex the records.
```
sudo docker exec -it ckan //usr/local/bin/ckan-paster --plugin=ckan search-index rebuild --config=/etc/ckan/production.ini
```

### you have done several builds of ckan and now you are running out of hard drive space? With ckan running you can
clean up docker images, containers, etc.
```
  docker system prune -a
```
or remove only the images you want with
```
	docker image ls
	docker rmi [image name]
```

### When creating orginizations or updating admin config settings you get a 500 Internal Server Error
This can be caused by ckan not having perissions to write to the intnernal storage of the ckan container. This should be setup during the build process. You can debug this by setting debug = true in the production.ini file. No error messages will be reported in the ckan logs for this issue without turning on debug.

To fix chage the owner of the ckan storage folder and its children
```
  sudo docker exec -u root -it ckan /bin/bash -c "export TERM=xterm; exec bash"
  chown -R ckan:ckan $CKAN_HOME $CKAN_VENV $CKAN_CONFIG $CKAN_STORAGE_PATH
  exit
```
---
