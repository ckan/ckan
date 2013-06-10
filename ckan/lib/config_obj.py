import logging
import os.path

from paste.deploy.converters import asbool

import ckan.lib.config_ini_parser as ini_parser

try:
    from collections import OrderedDict  # from python 2.7
except ImportError:
    from sqlalchemy.util import OrderedDict

log = logging.getLogger(__name__)


class _CkanConfig(object):

    _config = {}

    _config_sections = []
    _config_details = {}
    _config_store = []

    def __init__(self):
        path = os.path.join(os.path.dirname(__file__), '..', 'config')
        # parse the resource.config file if it exists
        config_path = os.path.join(path, 'config_options.ini')
        if os.path.exists(config_path):
            conf = ini_parser.ConfigIniParser(dict_type=OrderedDict)
            conf.read(config_path)
            for section in conf.sections():
                items = conf.items(section)
                items_dict = dict((n, v.strip()) for (n, v) in items)
                if section.startswith('section:'):
                    section_name = section[8:]
                    self._config_sections.append(
                        dict(name=section_name, options=[], **items_dict)
                    )
                else:
                    if 'type' not in items_dict:
                        items_dict['type'] = 'str'
                    self._config_details[section] = dict(section=section_name,
                                                         **items_dict)
                    self._config_sections[-1]['options'].append(section)

            ## FIXME
            ## These settings are strange
            ## ckan.favicon': {}, # default gets set in config.environment.py
            ## # has been setup in load_environment():
            ## ckan.site_id': {},

    def set_item(self, item, value):
        self._config[item] = value

    def clear(self):
        self._config = {}

    def items(self):
        return self._config.items()

    def get(self, key):
        if key.startswith('ckan.'):
            key = key[5:]
        return self._config.get(key.replace('.', '_'))

    __getitem__ = get

    def store_for_tests(self):
        self._config_store.append(self._config)

    def restore_for_tests(self):
        self._config = self._config_store.pop()

    def update_for_tests(self, items):
        self._config.update(items)

    def update(self, config):
        self.clear()
        for name, options in self._config_details.items():
            if 'name' in options:
                key = options['name']
            elif name.startswith('ckan.'):
                key = name[5:]
            else:
                key = name
            value = config.get(name, options.get('default', ''))

            data_type = options.get('type')
            if data_type == 'bool':
                value = asbool(value)
            elif data_type == 'int':
                value = int(value)
            elif data_type == 'split':
                value = value.split()
            key = key.replace('.', '_')
            self._config[key] = value

        # check for unknown options
        unknown_options = []
        for key in config.keys():
            if key.split('.')[0] in ['pylons', 'who', 'buffet', 'routes']:
                continue
            if key in ['here', '__file__', 'global_conf']:
                continue
            option = self._config_details.get(key)
            if not option:
                unknown_options.append(key)
        if unknown_options:
            msg = '\n\t'.join(unknown_options)
            log.warning('Unknown config option(s)\n\t%s' % msg)


ckan_config = _CkanConfig()
del _CkanConfig
