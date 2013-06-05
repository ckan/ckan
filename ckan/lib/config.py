import os.path
import logging

from pylons import config

import ckan.lib.config_ini_parser as ini_parser
import ckan.model as model

log = logging.getLogger(__name__)
# A place to store the origional config options of we override them
_CONFIG_CACHE = {}

config_sections = []
config_details = {}

path = os.path.join(os.path.dirname(__file__), '..', 'config')
# parse the resource.config file if it exists
config_path = os.path.join(path, 'config_options.ini')
if os.path.exists(config_path):
    conf = ini_parser.ConfigIniParser()
    conf.read(config_path)
    for section in conf.sections():
        items = conf.items(section)
        items_dict = dict((n, v.strip()) for (n, v) in items)
        if section.startswith('section:'):
            section_name = section[8:]
            config_sections.append(dict(name=section_name, options=[], **items_dict))
        else:
            if 'type' not in items_dict:
                items_dict['type'] = 'str'
            config_details[section] = dict(section=section_name, **items_dict)
            config_sections[-1]['options'].append(section)

    ## FIXME
    ## These settings are strange
    ## ckan.favicon': {}, # default gets set in config.environment.py
    ## # has been setup in load_environment():
    ## ckan.site_id': {},

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
