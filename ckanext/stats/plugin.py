import os
from logging import getLogger

from ckan.plugins import implements, SingletonPlugin
from ckan.plugins import IRoutes, IConfigurer

log = getLogger(__name__)

class StatsPlugin(SingletonPlugin):
    '''Stats plugin.'''

    implements(IRoutes, inherit=True)
    implements(IConfigurer, inherit=True)

    def after_map(self, map):
        map.connect('stats', '/stats',
            controller='ckanext.stats.controller:StatsController',
            action='index')
        map.connect('stats_action', '/stats/{action}',
            controller='ckanext.stats.controller:StatsController')
        return map

    def update_config(self, config):
        here = os.path.dirname(__file__)
        our_public_dir = os.path.join(here, 'public')
        template_dir = os.path.join(here, 'templates')
        config['extra_public_paths'] = ','.join([our_public_dir,
                config.get('extra_public_paths', '')])
        config['extra_template_paths'] = ','.join([template_dir,
                config.get('extra_template_paths', '')])
