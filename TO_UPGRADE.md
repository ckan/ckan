# BACKUP

```
cd ~/ckan/contrib/docker/postgresql
sudo bash ./pg_backup_rotated.sh
```

# Update config

Compare existing production.ini with template. make updates as needed. You may need to generate a new config file to populate some of the missing api keys.

```

```

```
export VOL_CKAN_CONFIG=`sudo docker volume inspect docker_ckan_config | jq -r -c '.[] | .Mountpoint'`
sudo cp $VOL_CKAN_CONFIG/production.ini ./production.ini.bak
sudo nano $VOL_CKAN_CONFIG/production.ini
```

Make sure you:

## add scheming_nerf_index to plugins

```bash
export VOL_CKAN_CONFIG=`sudo docker volume inspect docker_ckan_config | jq -r -c '.[] | .Mountpoint'`
sudo nano $VOL_CKAN_CONFIG/production.ini
```

In the file add the nerf plugin to list directly after other scheming plugins see production.ini templates for example.

```
  ckan.plugins =
    ...
    scheming_nerf_index
```

## Remove repeating and composit plugins

## Turn off tracking in the config, it doesn't seem to work

```
ckan.tracking_enabled = false
```

# Update who.ini

There are a few things that have changed in who.ini. First lets open the file.

```
export VOL_CKAN_HOME=`sudo docker volume inspect docker_ckan_home | jq -r -c '.[] | .Mountpoint'`
sudo cp $VOL_CKAN_HOME/venv/src/ckan/ckan/config/who.ini ./who.ini.bak
sudo nano $VOL_CKAN_HOME/venv/src/ckan/ckan/config/who.ini
```

Then update the following lines.

`use = ckan.lib.auth_tkt:make_plugin` to `use = ckan.lib.repoze_plugins.auth_tkt:make_plugin`

`use = repoze.who.plugins.friendlyform:FriendlyFormPlugin` to `use = ckan.lib.repoze_plugins.friendly_form:FriendlyFormPlugin`

# Clear the datasets!

Stop and clear all harvesters either through the admin interface or the API. 

We have to do this because the schema has changed and existing datasets
will not index properly.

**You will not be able to clear the harvester later so you must do it now.**

# Pull new ckan image

```
cd ~/ckan/contrib/docker
sudo docker-compose pull ckan
./clean_reload_ckan.sh
sudo docker-compose -f docker-compose.cpu_limited.yml --compatibility up -d
```

# Upgrade the database and build web assets?

```
sudo docker exec -it ckan ckan  --config=/etc/ckan/production.ini db upgrade

sudo docker exec -it ckan ckan  --config=/etc/ckan/production.ini asset build
```

# Rebuild indexes

```
sudo docker exec -it ckan ckan --config=/etc/ckan/production.ini search-index rebuild

sudo docker exec -it ckan ckan --config=/etc/ckan/production.ini harvester reindex
```

# Run this after updating ckan

```bash
sudo cp -r ../../ckan/migration $VOL_CKAN_HOME/venv/src/ckan/
sudo docker exec -u root -it ckan  /bin/bash -c "source ../bin/activate && python /usr/lib/ckan/venv/src/ckan/ckan/migration/migrate_package_activity.py -c /etc/ckan/production.ini"
```
