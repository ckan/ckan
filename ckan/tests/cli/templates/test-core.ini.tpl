[DEFAULT]
debug = false

[server:main]
use = egg:Paste#http
host = 0.0.0.0
port = 5000

[app:main]
use = egg:Paste#http
key1=%(here)s/core
key2=%(here)s/core
key4=core
