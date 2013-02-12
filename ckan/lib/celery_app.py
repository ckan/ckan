import ConfigParser
import os
import logging

from pylons import config as pylons_config
from pkg_resources import iter_entry_points, VersionConflict
#from celery.loaders.base import BaseLoader

log = logging.getLogger(__name__)

LIST_PARAMS = """CELERY_IMPORTS ADMINS ROUTES""".split()

from celery import Celery

celery = Celery()

config = ConfigParser.ConfigParser()

config_file = os.environ.get('CKAN_CONFIG')

if not config_file:
    config_file = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), '../../development.ini')
config.read(config_file)


sqlalchemy_url = pylons_config.get('sqlalchemy.url')
if not sqlalchemy_url:
    sqlalchemy_url = config.get('app:main', 'sqlalchemy.url')


default_config = dict(
    BROKER_BACKEND='sqlalchemy',
    BROKER_HOST=sqlalchemy_url,
    CELERY_RESULT_DBURI=sqlalchemy_url,
    CELERY_RESULT_BACKEND='database',
    CELERY_RESULT_SERIALIZER='json',
    CELERY_TASK_SERIALIZER='json',
    CELERY_IMPORTS=[],
)

for entry_point in iter_entry_points(group='ckan.celery_task'):
    try:
        default_config['CELERY_IMPORTS'].extend(
            entry_point.load()()
        )
    except VersionConflict, e:
        error = 'ERROR in entry point load: %s %s' % (entry_point, e)
        log.critical(error)
        pass

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
