python setup.py develop --user
ckan generate config ckan.ini
mkdir /workspace/data
ckan config-tool ckan.ini ckan.storage_path=/workspace/data
ckan config-tool ckan.ini ckan.site_url=https://$CODESPACE_NAME-5000.$GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN
ckan db init
ckan user add ckan_admin email=admin@example.com password=test1234
ckan sysadmin add ckan_admin
