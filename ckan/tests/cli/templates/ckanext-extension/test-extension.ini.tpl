[DEFAULT]
debug = true
smtp_server = localhost

[server:main]
use = egg:Paste#http
host = 0.0.0.0
port = 5000

[app:main]
use = config:../test-core.ini.tpl
key1=%(here)s/extension
key3=%(here)s/extension
key4=extension