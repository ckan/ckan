# Install CKAN locally
python setup.py develop --user

# Create ini file
ckan generate config ckan.ini

# Set up storage
mkdir /workspace/data
ckan config-tool ckan.ini ckan.storage_path=/workspace/data

# Set up Solr URL
ckan config-tool ckan.ini solr_url=http://localhost:8983/solr/ckan

# Set up site URL
ckan config-tool ckan.ini ckan.site_url=https://$CODESPACE_NAME-5000.$GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN

# Init DB
ckan db init

# Create sysadmin user
ckan user add ckan_admin email=admin@example.com password=test1234
ckan sysadmin add ckan_admin

# Set up DataStore + DataPusher
ckan config-tool ckan.ini "ckan.datapusher.api_token=$(ckan user token add ckan_admin datapusher | tail -n 1 | tr -d '\t')"
ckan config-tool ckan.ini \
    ckan.datastore.write_url=postgresql://ckan_default:pass@localhost/datastore_default \
    ckan.datastore.read_url=postgresql://datastore_default:pass@localhost/datastore_default \
    ckan.datapusher.url=http://localhost:8800 \
    ckan.datapusher.callback_url_base=http://localhost:5000 \
    "ckan.plugins=datastore datapusher datatables_view" \
    "ckan.views.default_views= image_view text_view datatables_view"

ckan datastore set-permissions | psql $(grep ckan.datastore.write_url ckan.ini | awk -F= '{print $2}')
