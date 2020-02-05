[DEFAULT]
debug = true
smtp_server = localhost
error_email_from = ckan-errors@example.com

[server:main]
use = egg:Paste#http
host = 0.0.0.0
port = 5000

[app:main]
use = config:test-core.ini.tpl
faster_db_test_hacks = True