[server:main]
port = 5000

[app:main]
debug = true
testing = true
ckan.auth.user_create_organizations = true
ckan.plugins = stats
