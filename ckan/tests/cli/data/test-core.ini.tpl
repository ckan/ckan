[server:main]
use = egg:Paste#http
host = 0.0.0.0
port = 5000

[app:main]
use = egg:ckan
full_stack = true
cache_dir = /tmp/%(ckan.site_id)s/
debug = false
testing = true

# Specify the Postgres database for SQLAlchemy to use
sqlalchemy.url = postgresql://ckan_default:pass@localhost/ckan_test

ckan.site_id = default

