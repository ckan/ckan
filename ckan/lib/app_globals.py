"""The application's Globals object"""

from paste.deploy.converters import asbool
from pylons import config

class Globals(object):

    """Globals acts as a container for objects available throughout the
    life of the application

    """

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
        print 'using css file %s' % self.main_css

    def set_global(self, key, value):
        setattr(self, key, value)

    def reset(self):
        ''' set updatable values from config '''

        self.site_title = config.get('ckan.site_title', '')
        self.site_logo = config.get('ckan.site_logo', '')
        self.site_url = config.get('ckan.site_url', '')
        self.site_description = config.get('ckan.site_description', '')
        self.site_about = config.get('ckan.site_about', '')

        # cusom styling
        self.set_main_css('/base/css/main.css')

    def __init__(self):
        """One instance of Globals is created during application
        initialization and is available during requests via the
        'app_globals' variable

        """

        self.reset()
        self.favicon = config.get('ckan.favicon',
                                  '/images/icons/ckan.ico')
        self.site_url_nice = self.site_url.replace('http://','').replace('www.','')
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

