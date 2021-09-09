## Update who.ini
use = ckan.lib.auth_tkt:make_plugin
to
use = ckan.lib.repoze_plugins.auth_tkt:make_plugin

use = repoze.who.plugins.friendlyform:FriendlyFormPlugin
to
use = ckan.lib.repoze_plugins.friendly_form:FriendlyFormPlugin




## Run this after updating ckan:
```bash
sudo docker exec -u root -it ckan  /bin/bash -c "python /usr/lib/ckan/venv/src/ckan/ckan/migration/migrate_package_activity.py -c /etc/ckan/production.ini"
```


## And scheming_nerf_index to plugins

```bash
export VOL_CKAN_CONFIG=`sudo docker volume inspect docker_ckan_config | jq -r -c '.[] | .Mountpoint'`
sudo nano $VOL_CKAN_CONFIG/production.ini
```

in file add plugin to list
```
  ckan.plugins =
    ...
    scheming_nerf_index
```
