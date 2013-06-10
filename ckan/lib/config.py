import logging

from pylons import config

import ckan.lib.config_obj as ckan_config
import ckan.model as model


log = logging.getLogger(__name__)


# A place to store the origional config options of we override them
_CONFIG_CACHE = {}


def get_config_value(key, default=''):
    if model.meta.engine.has_table('system_info'):
        value = model.get_system_info(key)
    else:
        value = None
    config_value = config.get(key)
    # sort encodeings if needed
    if isinstance(config_value, str):
        try:
            config_value = config_value.decode('utf-8')
        except UnicodeDecodeError:
            config_value = config_value.decode('latin-1')
    # we want to store the config the first time we get here so we can
    # reset them if needed
    if key not in _CONFIG_CACHE:
        _CONFIG_CACHE[key] = config_value
    if value is not None:
        log.debug('config `%s` set to `%s` from db' % (key, value))
    else:
        value = _CONFIG_CACHE[key]
        if value:
            log.debug('config `%s` set to `%s` from config' % (key, value))
        else:
            value = default
    # update the config
    config[key] = value
    return value


def config_items():
    return ckan_config.ckan_config.items()


def update_config():
    ckan_config.ckan_config.update(config)


def get_config(key):
    ''' Helper function for cleaner code '''
    return ckan_config.ckan_config.get(key)
