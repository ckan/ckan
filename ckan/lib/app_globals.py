''' The application's Globals object '''

import logging
import time
from threading import Lock
import re

from paste.deploy.converters import asbool
from pylons import config

import ckan
import ckan.model as model

log = logging.getLogger(__name__)


# mappings translate between config settings and globals because our naming
# conventions are not well defined and/or implemented
mappings = {
#   'config_key': 'globals_key',
}

# these config settings will get updated from system_info
auto_update = [
    'ckan.site_title',
    'ckan.site_logo',
    'ckan.site_url',
    'ckan.site_description',
    'ckan.site_about',
    'ckan.site_intro_text',
    'ckan.site_custom_css',
    'ckan.homepage_style',
]

config_details = {
    'ckan.favicon': {}, # default gets set in config.environment.py
    'ckan.template_head_end': {},
    'ckan.template_footer_end': {},
        # has been setup in load_environment():
    'ckan.site_id': {},
    'ckan.recaptcha.publickey': {'name': 'recaptcha_publickey'},
    'ckan.template_title_deliminater': {'default': '-'},
    'ckan.template_head_end': {},
    'ckan.template_footer_end': {},
    'ckan.dumps_url': {},
    'ckan.dumps_format': {},
    'ofs.impl': {'name': 'ofs_impl'},
    'ckan.homepage_style': {'default': '1'},

    # split string
    'search.facets': {'default': 'organization groups tags res_format license_id',
                      'type': 'split',
                      'name': 'facets'},
    'package_hide_extras': {'type': 'split'},
    'ckan.plugins': {'type': 'split'},

    # bool
    'openid_enabled': {'default': 'true', 'type' : 'bool'},
    'debug': {'default': 'false', 'type' : 'bool'},
    'ckan.debug_supress_header' : {'default': 'false', 'type' : 'bool'},
    'ckan.legacy_templates' : {'default': 'false', 'type' : 'bool'},
    'ckan.tracking_enabled' : {'default': 'false', 'type' : 'bool'},

    # int
    'ckan.datasets_per_page': {'default': '20', 'type': 'int'},
    'ckan.activity_list_limit': {'default': '30', 'type': 'int'},
    'search.facets.default': {'default': '10', 'type': 'int',
                             'name': 'facets_default_number'},
}


# A place to store the origional config options of we override them
_CONFIG_CACHE = {}

def set_main_css(css_file):
    ''' Sets the main_css using debug css if needed.  The css_file
    must be of the form file.css '''
    assert css_file.endswith('.css')
    if config.get('debug') and css_file == '/base/css/main.css':
        new_css = '/base/css/main.debug.css'
    else:
        new_css = css_file
    # FIXME we should check the css file exists
    app_globals.main_css = str(new_css)


def set_global(key, value):
    ''' helper function for getting value from database or config file '''
    model.set_system_info(key, value)
    setattr(app_globals, get_globals_key(key), value)
    model.set_system_info('ckan.config_update', str(time.time()))
    # update the config
    config[key] = value
    log.info('config `%s` set to `%s`' % (key, value))

def delete_global(key):
    model.delete_system_info(key)
    log.info('config `%s` deleted' % (key))

def get_globals_key(key):
    # create our globals key
    # these can be specified in mappings or else we remove
    # the `ckan.` part this is to keep the existing namings
    # set the value
    if key in mappings:
        return mappings[key]
    elif key.startswith('ckan.'):
        return key[5:]

def reset():
    ''' set updatable values from config '''
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
        setattr(app_globals, get_globals_key(key), value)
        # update the config
        config[key] = value
        return value

    # update the config settings in auto update
    for key in auto_update:
        get_config_value(key)

    # cusom styling
    main_css = get_config_value('ckan.main_css', '/base/css/main.css')
    set_main_css(main_css)
    # site_url_nice
    site_url_nice = app_globals.site_url.replace('http://', '')
    site_url_nice = site_url_nice.replace('www.', '')
    app_globals.site_url_nice = site_url_nice

    if app_globals.site_logo:
        app_globals.header_class = 'header-image'
    elif not app_globals.site_description:
        app_globals.header_class = 'header-text-logo'
    else:
        app_globals.header_class = 'header-text-logo-tagline'




class _Globals(object):

    ''' Globals acts as a container for objects available throughout the
    life of the application. '''

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
        self.ckan_base_version = re.sub('[^0-9\.]', '', self.ckan_version)
        if self.ckan_base_version == self.ckan_version:
            self.ckan_doc_version = 'ckan-{0}'.format(self.ckan_version)
        else:
            self.ckan_doc_version = 'latest'

        # process the config_details to set globals
        for name, options in config_details.items():
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

            setattr(self, key, value)


app_globals = _Globals()
del _Globals
