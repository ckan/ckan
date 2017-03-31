# encoding: utf-8

'''
Celery background tasks management.

This module is DEPRECATED, use ``ckan.lib.jobs`` instead.
'''

import ConfigParser
import logging
import os

from ckan.common import config as ckan_config
from pkg_resources import iter_entry_points, VersionConflict

from celery import __version__ as celery_version, Celery
if not celery_version.startswith(u'3.'):
    raise ImportError(u'Only Celery version 3.x is supported.')


log = logging.getLogger(__name__)

log.warning('ckan.lib.celery_app is deprecated, use ckan.lib.jobs instead.')

LIST_PARAMS = """CELERY_IMPORTS ADMINS ROUTES""".split()

celery = Celery()

config = ConfigParser.ConfigParser()

config_file = os.environ.get('CKAN_CONFIG')

if not config_file:
    config_file = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), '../../development.ini')
config.read(config_file)


sqlalchemy_url = ckan_config.get('sqlalchemy.url')
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

try:
    for key, value in config.items('app:celery'):
        if key in LIST_PARAMS:
            default_config[key.upper()] = value.split()
        else:
            default_config[key.upper()] = value
except ConfigParser.NoSectionError:
    pass

# Thes update of configuration means it is only possible to set each
# key once so this is done once all of the options have been decided.
celery.conf.update(default_config)
celery.loader.conf.update(default_config)
