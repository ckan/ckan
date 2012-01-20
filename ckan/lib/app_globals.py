"""The application's Globals object"""

from paste.deploy.converters import asbool
from pylons import config

class Globals(object):

    """Globals acts as a container for objects available throughout the
    life of the application

    """

    def __init__(self):
        """One instance of Globals is created during application
        initialization and is available during requests via the
        'app_globals' variable

        """
        self.site_title = config.get('ckan.site_title', '')
        self.favicon = config.get('ckan.favicon',
                                  '/images/icons/ckan.ico')
        self.site_logo = config.get('ckan.site_logo', '')
        self.site_url = config.get('ckan.site_url', '')
        self.site_url_nice = self.site_url.replace('http://','').replace('www.','')
        self.site_description = config.get('ckan.site_description', '')
        self.site_about = config.get('ckan.site_about', '')
        
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
        
