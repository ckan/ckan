[DEFAULT]
debug = true
smtp_server = localhost

[server:main]
use = egg:Paste#http
host = 0.0.0.0
port = 5000

[app:main]
use = config:test-core.ini.tpl

extension.custom_config = true

ckan.site_logo = /should_override_test_core_value.png