# Setup

These instructions are for CentOS 7. They have been modified from the original ['Installing CKAN with Docker Compose'](https://docs.ckan.org/en/2.8/maintaining/installing/install-from-docker-compose.html) instructions.

#### Install Docker

```
sudo apt-get update
sudo apt-get install docker
```

#### Install latest docker-compose

```bash
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

```bash
git clone -b cioos https://github.com/cioos-siooc/ckan.git
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

```bash
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

**Or** Use this setup if your site will run at yourdomain.com **/ckan**

```bash
cd ~/ckan/contrib/docker/
cp production_root_url.ini production.ini
cp who_root_url.ini who.ini
```

copy pyCSW config file and update the database password. This ist he same password enetered in your .env file

```bash
cd ~/ckan/contrib/docker/pycsw
cp pycsw.cfg.template pycsw.cfg
nano pycsw.cfg
```

---

#### Build CKAN

Change to ckan docker config folder

```bash
  cd ~/ckan/contrib/docker
```

Build containers

```bash
  sudo docker-compose up -d --build
```

if this fails try manually pulling the images first e.g.:

```bash
curl localhost:5000
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

```bash
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

```json
{
  "default_tags": ["geonetwork"],
  "default_extras": {
    "encoding": "utf8",
    "h_source_id": "{harvest_source_id}",
    "h_source_url": "https://hecate.hakai.org/geonetwork/srv/eng/catalog.search#/metadata/",
    "h_source_title": "{harvest_source_title}",
    "h_job_id": "{harvest_job_id}",
    "h_object_id": "{harvest_object_id}"
  },
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

```json
{
  "default_tags": ["erddap"],
  "default_extras": {
    "encoding": "utf8",
    "guid_suffix": "_iso19115.xml",
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

#### 19115-3 WAF (ERDDAP)

```json
{
  "default_tags": [],
  "default_extras": {
    "encoding": "utf8",
    "h_source_id": "{harvest_source_id}",
    "h_source_url": "{harvest_source_url}",
    "h_source_title": "{harvest_source_title}",
    "h_job_id": "{harvest_job_id}",
    "h_object_id": "{harvest_object_id}"
  },
  "override_extras": false,
  "clean_tags": true,
  "validator_profiles": ["iso19115"],
  "remote_orgs": "only_local",
  "harvest_iso_categories": false,
  "organization_mapping": {
    "Institute of Ocean Sciences, 9860 West Saanich Road, Sidney, B.C., Canada": "Fisheries and Oceans Canada"
  }
}
```

#### CKAN

```json
{
  "default_tags": [{ "name": "ckan" }, { "name": "production" }],
  "default_extras": {
    "encoding": "utf8",
    "h_source_id": "{harvest_source_id}",
    "h_source_url": "{harvest_source_url}",
    "h_source_title": "{harvest_source_title}",
    "h_job_id": "{harvest_job_id}",
    "h_object_id": "{harvest_object_id}"
  },
  "clean_tags": true,
  "remote_groups": "create",
  "remote_orgs": "create",
  "use_default_schema": true,
  "force_package_type": "dataset",
  "groups_filter_include": ["cioos"],
  "spatial_crs": "4326",
  "spatial_filter_file": "./cioos-siooc-schema/pacific_RA.wkt",
  "spatial_filter": "POLYGON((-128.17701209 51.62096599, -127.92157996 51.62096599, -127.92157996 51.73507366, -128.17701209 51.73507366, -128.17701209 51.62096599))"
}
```
Note that `use_default_schema` and `force_package_type` are not needed and will cause validation errors if harvesting between two ckans using the same custom schema (the CIOOS setup). `spatial_filter_file`, if set, will take presidents over `spatial_filter`. Thus in the above example the `spatial_filter` paramiter will be ignored in favour of loading the spatial filter from an external file

### reindex Harvesters
it may become nesisary to reindex harvesters, especially if they no longer report the correct number of harveted datasets. If modifying the harvester config you will also need to reindex to make the new config take affect

```bash
sudo docker exec -it ckan /usr/local/bin/ckan-paster --plugin=ckanext-harvest harvester reindex --config=/etc/ckan/production.ini
```
---

#### Finish setting up pyCSW

create pycsw database in existing pg container and install postgis

```bash
sudo docker exec -it db psql -U ckan
CREATE DATABASE pycsw OWNER ckan ENCODING 'utf-8';
\c pycsw
CREATE EXTENSION postgis;
\q
```

setup pycsw database tables.

```bash
sudo docker exec -it ckan /usr/local/bin/ckan-paster --plugin=ckanext-spatial ckan-pycsw setup -p /usr/lib/ckan/venv/src/pycsw/default.cfg
```

start pycsw container

```bash
sudo docker-compose up -d pycsw
```

#### test GetCapabilities

<https://localhost/ckan/csw/?service=CSW&version=2.0.2&request=GetCapabilities>

or

<https://localhost/csw/?service=CSW&version=2.0.2&request=GetCapabilities>

#### Useful pycsw commands

access pycsw-admin

```bash
sudo docker exec -ti pycsw pycsw-admin.py -h
```

Load the CKAN datasets into pycsw

```bash
sudo docker exec -it ckan /usr/local/bin/ckan-paster --plugin=ckanext-spatial ckan-pycsw load -p /usr/lib/ckan/venv/src/pycsw/default.cfg -u http://localhost:5000
```

ckan-pycsw commands

```bash
sudo docker exec -it ckan /usr/local/bin/ckan-paster --plugin=ckanext-spatial ckan-pycsw --help
sudo docker exec -it ckan /usr/local/bin/ckan-paster --plugin=ckanext-spatial ckan-pycsw setup -p /usr/lib/ckan/venv/src/pycsw/default.cfg
sudo docker exec -it ckan /usr/local/bin/ckan-paster --plugin=ckanext-spatial ckan-pycsw set_keywords -p /usr/lib/ckan/venv/src/pycsw/default.cfg -u http://localhost:5000
sudo docker exec -it ckan /usr/local/bin/ckan-paster --plugin=ckanext-spatial ckan-pycsw load -p /usr/lib/ckan/venv/src/pycsw/default.cfg -u http://localhost:5000
sudo docker exec -it ckan /usr/local/bin/ckan-paster --plugin=ckanext-spatial ckan-pycsw clear -p /usr/lib/ckan/venv/src/pycsw/default.cfg
```

errors while pycsw loading
if you get "Error:Cannot commit to repository" and "HINT: Values larger than 1/3 of a buffer page cannot be indexed." you are likely loading abstracts or other fields that are to big to be indexed in the database. You can either remove the index or switch to an index using the md5 encoded version of the value.

connect to db

```bash
sudo docker exec -i db psql -U ckan
\c pycsw
```

remove index

```sql
DROP INDEX ix_records_abstract;
```

add md5 index

```sql
CREATE INDEX ix_records_abstract ON records((md5(abstract)));
```

---

#### Setup Apache proxy

CKAN by default will install to localhost:5000. You can use Apache to forward requests from yourdomain.com or yourdomain.com/ckan to localhost:5000.

#### Install Apache

If proxying docker behind Apache (recommended) you will need to have that installed as well. nginx will also work but is not covered in this guide.

```bash
sudo yum install httpd mod_ssl
sudo systemctl enable httpd
sudo systemctl start httpd
```

add the following to your sites configs

```apache
    # CKAN
		<location /ckan>
  	    ProxyPass http://localhost:5000/
  	    ProxyPassReverse http://localhost:5000/
        # enable deflate
        SetOutputFilter DEFLATE
        SetEnvIfNoCase Request_URI "\.(?:gif|jpe?g|png)$" no-gzip
   	</location>

    # pycsw
     <location /ckan/csw>
         ProxyPass http://localhost:8000/pycsw/csw.js
         ProxyPassReverse http://localhost:8000/pycsw/csw.js
    </location>
```

or

```apache
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

Redirect HTTP to HTTPS

```apache
<VirtualHost *:80>
   Redirect / https://yourdomain.org
</VirtualHost>
```

Allow Apache to make network connections:

```bash
sudo /usr/sbin/setsebool -P httpd_can_network_connect 1
```

Restart apache

```bash
  sudo apachectl restart
```

# Enable Compression in Apache
ubuntu https://rietta.com/blog/moddeflate-dramatic-website-speed/
centos7 https://www.digitalocean.com/community/tutorials/how-to-install-and-configure-mod_deflate-on-centos-7
Enable mod_deflate in your Apache2 installation

```bash
sudo a2enmod deflate
```

Restart apache
```bash
  sudo apachectl restart
```

# Customize interface
Now that you have ckan running you can customize the interface via the admin config page. Go to http://localhost:5000/ckan-admin/config and configure some of the site options.

- Site_logo can be used to set the CIOOS logo that appears on every page.
- Homepage should be set to CIOOS for the CIOOS style home page layout
- Custom CSS can be used to change the colour pallet of the site as well as any of the other css items. An example css that sets the colour pallet is:

```CSS
.box, .wrapper {
    border: 1px solid #006e90;
    border-width: 0 0 0 4px;
}

#topmenu {
    background: #006e90;
}

.account-masthead{
  background-image: none;
  background: #006e90;
}

#footer{
  background: #006e90;
}


#footer a {
  color: rgb(255,255,255,.5);
}
.account-masthead .account ul li a {
  color: rgb(255,255,255,.5);
}
```

---

# Troubleshooting

Issues building/starting CKAN:

Try manually pulling the images first e.g.:

```bash
  sudo docker pull --disable-content-trust clementmouchet/datapusher
  sudo docker pull --disable-content-trust redis:latest
```

Sometimes the containers start in the wrong order. This often results in strange sql errors in the db logs. If this happens you can manually start the containers by first building then using docker-compose up

```bash
  sudo docker-compose build
  sudo docker-compose up -d db
  sudo docker-compose up -d solr redis
  sudo docker-compose up -d ckan
  sudo docker-compose up -d datapusher
  sudo docker-compose up -d ckan_gather_harvester ckan_fetch_harvester ckan_run_harvester
```

if you need to change the production.ini in the repo and rebuild then you may need to delete the volume first. volume does not update during dockerfile run if it already exists.

```bash
  sudo docker-compose down
  sudo docker volume rm docker_ckan_config
```

update ckan/contrib/docker/production.ini

```bash
  export VOL_CKAN_CONFIG=`sudo docker volume inspect docker_ckan_config | jq -r -c '.[] | .Mountpoint'`
  sudo nano $VOL_CKAN_CONFIG/production.ini
```

on windows edit the production.ini file and copy it to the volume
```bash
  docker cp production.ini ckan:/etc/ckan/
```

Is ckan running? Check container is running and view logs

```bash
  sudo docker ps | grep ckan
  sudo docker-compose logs -f ckan
```

if container isn’t running its probably because the db didn’t build in time. restart…

```bash
  sudo docker-compose restart ckan
```

Connect to container as root to debug

```bash
  sudo docker exec -u root -it ckan /bin/bash -c "export TERM=xterm; exec bash"
```

If you rebuilt the ckan container and no records are showing up, you need to reindex the records.

```bash
sudo docker exec -it ckan /usr/local/bin/ckan-paster --plugin=ckan search-index rebuild --config=/etc/ckan/production.ini
```

you have done several builds of ckan and now you are running out of hard drive space? With ckan running you can clean up docker images, containers, volumes, cache etc.

```bash
  sudo docker system prune -a
  sudo docker volume prune
```

or remove only the images you want with

```bash
	sudo docker image ls
	sudo docker rmi [image name]
```

#### When creating organizations or updating admin config settings you get a 500 Internal Server Error

This can be caused by ckan not having permissions to write to the internal storage of the ckan container. This should be setup during the build process. You can debug this by setting debug = true in the production.ini file. No error messages will be reported in the ckan logs for this issue without turning on debug.

To fix chage the owner of the ckan storage folder and its children

```bash
  sudo docker exec -u root -it ckan /bin/bash -c "export TERM=xterm; exec bash"
  chown -R ckan:ckan $CKAN_HOME $CKAN_VENV $CKAN_CONFIG $CKAN_STORAGE_PATH
  exit
```

#### Build fails with 'Temporary failure resolving...' errors

Likely the issue is that docker is passing the wrong DNS lookup addresses to the
containers on build. See issue this issue on stack overflow https://stackoverflow.com/a/45644890
for a solution.

---
# Update solr schema

This method uses dockers copy command to copy the new schema file into a running
solr container

```bash
cd ~/ckan
sudo docker cp ~/ckan/ckan/config/solr/schema.xml solr:/opt/solr/server/solr/ckan/conf
```

restart solr container

```bash
cd ~/ckan/contrib/docker
sudo docker-compose restart solr
```

rebuild search index

```bash
sudo docker exec -it ckan /usr/local/bin/ckan-paster --plugin=ckan search-index rebuild --config=/etc/ckan/production.ini
```

# Update CKAN
If you need to update CKAN to a new version you can either remove the docker_ckan_home volume or update the volume with the new ckan core files. After which you need to rebuild the CKAN image and any docker containers based on that image. If you are working with a live / production system the prefered method is to update the volume and rebuild which will result in the least amount of down time.

update local repo
```bash
cd ~/ckan
git pull
```

Then copy updated ckan core files into the volume

```bash
cd ~/ckan
sudo cp -r . $VOL_CKAN_HOME/venv/src/ckan
```

update permissions (optional but recommended)

```bash
sudo chown 900:900 -R $VOL_CKAN_HOME/venv/src/
```
or on windows run the command directly in the ckan container

```bash
sudo docker exec -it ckan chown 900:900 -R $CKAN_HOME
```

Now rebuild the CKAN docker image

```bash
cd ~/ckan/contrib/docker
sudo docker-compose build ckan
```

update affected containers.

```bash
cd ~/ckan/contrib/docker
sudo docker-compose up -d
```

# Update CKAN extensions

enable volume environment variables to make accessing the volumes easier

```bash
export VOL_CKAN_HOME=`sudo docker volume inspect docker_ckan_home | jq -r -c '.[] | .Mountpoint'`
export VOL_CKAN_CONFIG=`sudo docker volume inspect docker_ckan_config | jq -r -c '.[] | .Mountpoint'`
export VOL_CKAN_STORAGE=`sudo docker volume inspect docker_ckan_storage | jq -r -c '.[] | .Mountpoint'`
echo $VOL_CKAN_HOME
echo $VOL_CKAN_CONFIG
echo $VOL_CKAN_STORAGE
```

update submodules

```bash
cd ~/ckan
git pull
git submodule init
git submodule sync
git submodule update
```

copy updated extension code to the volumes

```bash
cd ~/ckan/contrib/docker
sudo cp -r src/ckanext-cioos_theme/ $VOL_CKAN_HOME/venv/src/
sudo cp -r src/ckanext-cioos_harvest/ $VOL_CKAN_HOME/venv/src/
sudo cp -r src/ckanext-harvest/ $VOL_CKAN_HOME/venv/src/
sudo cp -r src/ckanext-spatial/ $VOL_CKAN_HOME/venv/src/
sudo cp -r src/pycsw/ $VOL_CKAN_HOME/venv/src/
sudo cp -r src/ckanext-scheming/ $VOL_CKAN_HOME/venv/src/
sudo cp -r src/ckanext-package_converter/ $VOL_CKAN_HOME/venv/src/
sudo cp -r src/ckanext-fluent/ $VOL_CKAN_HOME/venv/src/
sudo cp src/cioos-siooc-schema/cioos-siooc_schema.json $VOL_CKAN_HOME/venv/src/ckanext-scheming/ckanext/scheming/cioos_siooc_schema.json
sudo cp src/cioos-siooc-schema/organization.json $VOL_CKAN_HOME/venv/src/ckanext-scheming/ckanext/scheming/organization.json
sudo cp src/cioos-siooc-schema/ckan_license.json $VOL_CKAN_HOME/venv/src/ckan/contrib/docker/src/cioos-siooc-schema/ckan_license.json
```

update permissions

```bash
cd ~/ckan/contrib/docker
docker cp -r src/ckanext-cioos_theme/ ckan:/usr/lib/ckan/venv/src/
docker cp -r src/ckanext-cioos_harvest/ ckan:/usr/lib/ckan/venv/src/
docker cp -r src/ckanext-harvest/ ckan:/usr/lib/ckan/venv/src/
docker cp -r src/ckanext-spatial/ ckan:/usr/lib/ckan/venv/src/
docker cp -r src/pycsw/ ckan:/usr/lib/ckan/venv/src/
docker cp -r src/ckanext-scheming/ ckan:/usr/lib/ckan/venv/src/
docker cp -r src/ckanext-repeating/ ckan:/usr/lib/ckan/venv/src/
docker cp -r src/ckanext-composite/ ckan:/usr/lib/ckan/venv/src/
docker cp -r src/ckanext-package_converter/ ckan:/usr/lib/ckan/venv/src/
docker cp -r src/ckanext-fluent/ ckan:/usr/lib/ckan/venv/src/
docker cp src/cioos-siooc-schema/cioos-siooc_schema.json ckan:/usr/lib/ckan/venv/src/ckanext-scheming/ckanext/scheming/cioos_siooc_schema.json
docker cp src/cioos-siooc-schema/organization.json ckan:/usr/lib/ckan/venv/src/ckanext-scheming/ckanext/scheming/organization.json
```

update permissions (optional)

```bash
sudo chown 900:900 -R $VOL_CKAN_HOME/venv/src/
```

```bash
docker exec -u root -it ckan chown 900:900 -R /usr/lib/ckan
```

restart the container affected by the change. If changing html files you may not need to restart anything

```bash
cd ~/ckan/contrib/docker
sudo docker-compose restart ckan
sudo docker-compose restart ckan_run_harvester ckan_fetch_harvester ckan_gather_harvester
```

### update a system file in a running container
The easiest way is with the docker copy command. For example to update the crontab of the ckan_run_harvester containers you first copy the file to the container:

```base
cd ~/ckan/contrib/docker
sudo docker cp ./crontab ckan_run_harvester:/etc/cron.d/crontab
```

Then update the crontab in the container by connecting to it's bash shell and running the crontab commands

```base
sudo docker exec -u root -it ckan_run_harvester /bin/bash -c "export TERM=xterm; exec bash"
chown root:root /etc/cron.d/crontab
chmod 0644 /etc/cron.d/crontab
/usr/bin/crontab /etc/cron.d/crontab
exit
```

In this example the entrypoint file for this container also copies the file over from the volume so you should update the file in the volume as well so that when the container is restarted the correct file contents is used.
```base
cd ~/ckan/contrib/docker
sudo cp -r ./crontab $VOL_CKAN_HOME/venv/src/ckan/contrib/docker/crontab
```

### Set timezone

timedatectl
ls -l /etc/localtime
timedatectl list-timezones
sudo timedatectl set-timezone UTC
sudo timedatectl set-timezone America/Vancouver



sudo docker exec -it ckan /usr/local/bin/ckan-paster --plugin=ckan post -c /etc/ckan/production.ini /api/action/send_email_notifications

### get public ip of server
```bash
curl ifconfig.me
```
