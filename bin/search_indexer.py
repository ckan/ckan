import os, sys
import paste.deploy
import ckan.config.environment

usage = '''
Postgres search indexer
=======================
    Usage: pyenv/bin/python bin/search_indexer.py development.ini'''
if len(sys.argv) != 2:
    print usage
    sys.exit(1)

# load config
config_path = os.path.abspath(sys.argv[1])
conf = paste.deploy.appconfig('config:' + config_path)
ckan.config.environment.load_environment(conf.global_conf, conf.local_conf)
from pylons import config

# start indexer
from ckan.model import SearchIndexManager
indexer = SearchIndexManager()
indexer.clear_queue()
while True:
    indexer.run()
