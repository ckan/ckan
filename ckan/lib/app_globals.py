"""The application's Globals object"""
import logging

from paste.deploy.converters import asbool
from pylons import config

import ckan.model as model

log = logging.getLogger(__name__)

class Globals(object):

    """Globals acts as a container for objects available throughout the
    life of the application

    """

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
    ]

    def set_main_css(self, css_file):
        ''' Sets the main_css using debug css if needed.  The css_file
        must be of the form file.css '''
        assert css_file.endswith('.css')
        if config.debug and css_file == 'base/css/main.css':
            new_css = 'base/css/main.debug.css'
        else:
            new_css = css_file
        # FIXME we should check the css file exists
        self.main_css = str(new_css)

    def set_global(self, key, value):
        ''' helper function for getting value from database or config file '''
        model.set_system_info(key, value)
        setattr(self, self.mappings[key], value)
        # update the config
        config[key] = value
        log.info('config `%s` set to `%s`' % (key, value))

    def reset(self):
        ''' set updatable values from config '''

        def grab(key, default=''):
            value = model.get_system_info(key)
            if value:
                # update the config
                config[key] = value
                log.info('config `%s` set to `%s` from db' % (key, value))
            else:
                value = config.get(key, default)
            # create our globals key
            # these can be specified in self.mappings or else we remove
            # the `ckan.` part this is to keep the existing namings
            if key in self.mappings:
                key = self.mappings[key]
            elif key.startswith('ckan.'):
                key = key[5:]
            # set the value
            setattr(self, key, value)
            return value

        # update the config settings in auto update
        for key in self.auto_update:
            grab(key)

        # cusom styling
        self.set_main_css(grab('ckan.main_css', '/base/css/main.css'))

        self.site_url_nice = self.site_url.replace('http://','').replace('www.','')

    def __init__(self):
        """One instance of Globals is created during application
        initialization and is available during requests via the
        'app_globals' variable

        """

        self.favicon = config.get('ckan.favicon',
                                  '/images/icons/ckan.ico')
        self.facets = config.get('search.facets', 'groups tags res_format license').split()

        # has been setup in load_environment():
        self.site_id = config.get('ckan.site_id')

        self.template_head_end = config.get('ckan.template_head_end', '')
        self.template_footer_end = config.get('ckan.template_footer_end', '')

        # hide these extras fields on package read
        self.package_hide_extras = config.get('package_hide_extras', '').split()

        self.openid_enabled = asbool(config.get('openid_enabled', 'true'))

        self.recaptcha_publickey = config.get('ckan.recaptcha.publickey', '')
        self.recaptcha_privatekey = config.get('ckan.recaptcha.privatekey', '')

        self.datasets_per_page = int(config.get('ckan.datasets_per_page', '20'))

