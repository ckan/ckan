# encoding: utf-8

''' The application's Globals object '''
from __future__ import annotations

import logging
import re
from threading import Lock
from typing import Any, Union

import ckan
import ckan.model as model
from ckan.logic.schema import update_configuration_schema
from ckan.common import asbool, config, aslist


log = logging.getLogger(__name__)


DEFAULT_MAIN_CSS_FILE = '/base/css/main.css'

# mappings translate between config settings and globals because our naming
# conventions are not well defined and/or implemented
mappings: dict[str, str] = {
#   'config_key': 'globals_key',
}


# This mapping is only used to define the configuration options (from the
# `config` object) that should be copied to the `app_globals` (`g`) object.
app_globals_from_config_details: dict[str, dict[str, str]] = {
    'ckan.site_title': {},
    'ckan.site_logo': {},
    'ckan.site_url': {},
    'ckan.site_description': {},
    'ckan.site_about': {},
    'ckan.site_intro_text': {},
    'ckan.site_custom_css': {},
    'ckan.favicon': {}, # default gets set in config.environment.py
    'ckan.template_head_end': {},
    'ckan.template_footer_end': {},
        # has been setup in load_environment():
    'ckan.site_id': {},
    'ckan.recaptcha.publickey': {'name': 'recaptcha_publickey'},
    'ckan.template_title_delimiter': {'default': '-'},
    'ckan.template_head_end': {},
    'ckan.template_footer_end': {},
    'ckan.dumps_url': {},
    'ckan.dumps_format': {},
    'ckan.homepage_style': {'default': '1'},

    # split string
    'search.facets': {'default': 'organization groups tags res_format license_id',
                      'type': 'split',
                      'name': 'facets'},
    'package_hide_extras': {'type': 'split'},
    'ckan.plugins': {'type': 'split'},

    # bool
    'debug': {'default': 'false', 'type' : 'bool'},
    'ckan.debug_supress_header' : {'default': 'false', 'type' : 'bool'},
    'ckan.tracking_enabled' : {'default': 'false', 'type' : 'bool'},

    # int
    'ckan.datasets_per_page': {'default': '20', 'type': 'int'},
    'ckan.activity_list_limit': {'default': '30', 'type': 'int'},
    'ckan.user_list_limit': {'default': '20', 'type': 'int'},
    'search.facets.default': {'default': '10', 'type': 'int',
                             'name': 'facets_default_number'},
}


# A place to store the origional config options of we override them
_CONFIG_CACHE: dict[str, Any] = {}

def set_main_css(css_file: str) -> None:
    ''' Sets the main_css.  The css_file must be of the form file.css '''
    assert css_file.endswith('.css')
    new_css = css_file
    # FIXME we should check the css file exists
    app_globals.main_css = str(new_css)


def set_app_global(key: str, value: str) -> None:
    '''
    Set a new key on the app_globals (g) object

    It will process the value according to the options on
    app_globals_from_config_details (if any)
    '''
    key, new_value = process_app_global(key, value)
    setattr(app_globals, key, new_value)


def process_app_global(
        key: str, value: str) -> tuple[str, Union[bool, int, str, list[str]]]:
    '''
    Tweak a key, value pair meant to be set on the app_globals (g) object

    According to the options on app_globals_from_config_details (if any)
    '''
    options = app_globals_from_config_details.get(key)
    key = get_globals_key(key)
    new_value: Any = value
    if options:
        if 'name' in options:
            key = options['name']
        value = value or options.get('default', '')

        data_type = options.get('type')
        if data_type == 'bool':
            new_value = asbool(value)
        elif data_type == 'int':
            new_value = int(value)
        elif data_type == 'split':
            new_value = aslist(value)
        else:
            new_value = value
    return key, new_value


def get_globals_key(key: str) -> str:
    # create our globals key
    # these can be specified in mappings or else we remove
    # the `ckan.` part this is to keep the existing namings
    # set the value
    if key in mappings:
        return mappings[key]
    elif key.startswith('ckan.'):
        return key[5:]
    else:
        return key


def reset() -> None:
    ''' set updatable values from config '''
    def get_config_value(key: str, default: str = ''):
        # type_ignore_reason: engine theoretically uninitialized
        if model.meta.engine.has_table('system_info'):  # type: ignore
            value = model.get_system_info(key)
        else:
            value = None
        config_value = config.get(key)
        # sort encodeings if needed

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

        set_app_global(key, value)

        # update the config
        config[key] = value

        return value

    # update the config settings in auto update
    schema = update_configuration_schema()
    for key in schema.keys():
        get_config_value(key)

    # custom styling
    main_css = get_config_value(
        'ckan.main_css', DEFAULT_MAIN_CSS_FILE) or DEFAULT_MAIN_CSS_FILE
    set_main_css(main_css)

    if app_globals.site_logo:
        app_globals.header_class = 'header-image'
    elif not app_globals.site_description:
        app_globals.header_class = 'header-text-logo'
    else:
        app_globals.header_class = 'header-text-logo-tagline'


class _Globals(object):
    ''' Globals acts as a container for objects available throughout the
    life of the application. '''

    main_css: str
    site_logo: str
    header_class: str
    site_description: str

    def __init__(self):
        '''One instance of Globals is created during application
        initialization and is available during requests via the
        'app_globals' variable
        '''
        self._init()
        self._config_update = None
        self._mutex = Lock()

    def _check_uptodate(self):
        ''' check the config is uptodate needed when several instances are
        running '''
        value = model.get_system_info('ckan.config_update')
        if self._config_update != value:
            if self._mutex.acquire(False):
                reset()
                self._config_update = value
                self._mutex.release()

    def _init(self):

        self.ckan_version = ckan.__version__
        self.ckan_base_version = re.sub(r'[^0-9\.]', '', self.ckan_version)
        if self.ckan_base_version == self.ckan_version:
            self.ckan_doc_version = self.ckan_version[:3]
        else:
            self.ckan_doc_version = 'latest'
        # process the config details to set globals
        for key in app_globals_from_config_details.keys():
            new_key, value = process_app_global(key, config.get(key) or '')
            setattr(self, new_key, value)


app_globals = _Globals()
del _Globals
