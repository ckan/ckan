''' The application's Globals object '''

import logging
import time
from threading import Lock
import re

from pylons import config

import ckan
import ckan.lib.config as lib_config
import ckan.model as model

log = logging.getLogger(__name__)

# these config settings will get updated from system_info
auto_update = [
    'ckan.site_title',
    'ckan.site_logo',
    'ckan.site_url',
    'ckan.site_description',
    'ckan.site_about',
    'ckan.site_intro_text',
    'ckan.site_custom_css',
]

def reset_globals():
    ''' set updatable values from config '''

    # update the config settings in auto update
    for key in auto_update:
        value = lib_config.get_config_value(key)
        setattr(app_globals, get_globals_key(key), value)

    # cusom styling
    main_css = lib_config.get_config_value('ckan.main_css', '/base/css/main.css')
    setattr(app_globals, get_globals_key(key), main_css)
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
    # Create our globals key. We remove the `ckan.` part this is to keep the
    # existing namings set the value
    if key.startswith('ckan.'):
        return key[5:]





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
                reset_globals()
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
        lib_config.update_config()
        for key, value in lib_config.config_items():
            setattr(self, key, value)


app_globals = _Globals()
del _Globals
