# ckanext-logs

## Requirements
Compatibility with core CKAN versions:

| CKAN version    | Compatible?   |
| --------------- | ------------- |
| 2.10 and earlier| not tested    |
| 2.10.4          | yes           |

## Installation
To install ckanext-logs:

1. Activate your CKAN virtual environment, for example:
```bash
. /usr/lib/ckan/default/bin/activate
```

2. Clone the source and install it on the virtualenv
```bash
git clone https://github.com/vanquan223/ckanext-logs.git
cd ckanext-logs
pip install -e .
pip install -r requirements.txt
```

3. Add `logs` to the `ckan.plugins` setting in your CKAN
   config file (by default the config file is located at
   `/etc/ckan/default/ckan.ini`).

4. Restart CKAN. For example if you've deployed CKAN with Apache on Ubuntu:
```bash
sudo service apache2 reload
```

## Config settings
```bash
## ckanext-logs ##############################################
ckan.logs.url = http://10.70.123.8:30092
ckan.logs.username = elastic
ckan.logs.password = Vnpt@1234
ckan.logs.limit = 10
ckan.logstash.host= 10.70.123.8
ckan.logstash.port = 4560
ckan.logstash.type = logstash
ckan.logstash.kind = tcp
ckan.logstash.configure_logging = TRUE
ckan.logstash.log_level = WARN
ckan.logstash.message_type = opendata_local
```

## License

[AGPL](https://www.gnu.org/licenses/agpl-3.0.en.html)
