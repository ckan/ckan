"""The application's Globals object"""

from paste.deploy.converters import asbool
from pylons import config

import ckan.model as model

def get_system_info(key, default=None):
    ''' get data from system_info table '''
    obj = model.Session.query(model.SystemInfo).filter_by(key=key).first()
    if obj:
        return obj.value
    else:
        return default

def set_system_info(key, value):
    ''' save data in the system_info table '''

    obj = None
    obj = model.Session.query(model.SystemInfo).filter_by(key=key).first()
    if obj and obj.value == unicode(value):
        return
    if not obj:
        obj = model.SystemInfo(key, value)
    else:
        obj.value = unicode(value)
    model.Session.add(obj)
    model.Session.commit()

class Globals(object):

    """Globals acts as a container for objects available throughout the
    life of the application

    """

    # mappings translate between config settings and globals because our naming
    # conventions are not defined and/or implemented
    mappings = {
        'ckan.site_title': 'site_title',
        'ckan.site_logo': 'site_logo',
        'ckan.site_url': 'site_url',
        'ckan.site_description': 'site_description',
        'ckan.site_about': 'site_about',
        'ckan.main_css': 'main_css',
    }

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
        set_system_info(key, value)
        setattr(self, self.mappings[key], value)

    def reset(self):
        ''' set updatable values from config '''

        def grab(key, default):
            value = get_system_info(key, config.get(key, default))
            setattr(self, self.mappings[key], value)

        grab('ckan.site_title', '')
        grab('ckan.site_logo', '')
        grab('ckan.site_url', '')
        grab('ckan.site_description', '')
        grab('ckan.site_about', '')

        # cusom styling
        self.set_main_css(get_system_info('ckan.main_css',
                config.get('ckan.main_css','/base/css/main.css')))

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

