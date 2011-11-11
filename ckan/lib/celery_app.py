import ConfigParser
import os
from pkg_resources import iter_entry_points
#from celery.loaders.base import BaseLoader

LIST_PARAMS = """CELERY_IMPORTS ADMINS ROUTES""".split()

from celery import Celery

celery = Celery()

config = ConfigParser.ConfigParser()

config_file = os.environ.get('CKAN_CONFIG')
if not config_file:
    config_file =  os.path.join(
        os.path.dirname(os.path.abspath(__file__)), '../../development.ini')
config.read(config_file)


default_config = dict( 
    BROKER_BACKEND = 'sqlalchemy',
    BROKER_HOST = config.get('app:main', 'sqlalchemy.url'),
    CELERY_RESULT_DBURI = config.get('app:main', 'sqlalchemy.url'),
    CELERY_RESULT_BACKEND = 'database',
    CELERY_RESULT_SERIALIZER = 'json',
    CELERY_TASK_SERIALIZER = 'json',
    CELERY_IMPORTS = [],
)

for entry_point in iter_entry_points(group='ckan.celery_task'):
    default_config['CELERY_IMPORTS'].extend(
        entry_point.load()()
    )


celery.conf.update(default_config)
celery.loader.conf.update(default_config)

try:
    for key, value in config.items('app:celery'):
        if key in LIST_PARAMS:
            celery.conf[key.upper()] = value.split()
            celery.loader.conf[key.upper()] = value.split()
        else:
            celery.conf[key.upper()] = value
            celery.loader.conf[key.upper()] = value.split()
except ConfigParser.NoSectionError:
    pass
