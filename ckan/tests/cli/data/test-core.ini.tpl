[DEFAULT]
debug = false

[server:main]
use = egg:Paste#http
host = 0.0.0.0
port = 5000

[app:main]
use = egg:ckan
full_stack = true
cache_dir = /tmp/%(ckan.site_id)s/
testing = true
ckan.site_id = default
ckan.site_logo = /path_to_logo.png
sqlalchemy.url = postgresql://ckan_default:pass@localhost/ckan_test

