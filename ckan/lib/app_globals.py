"""The application's Globals object"""

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
        self.site_title = config.get('ckan.site_title', 'CKAN')
        self.site_url = config.get('ckan.site_url', 'http://www.ckan.net')
        
        # has been setup in load_environment():
        self.site_id = config.get('ckan.site_id')