# encoding: utf-8

from logging import getLogger

import ckan.plugins as p
from ckanext.stats import blueprint

log = getLogger(__name__)


class StatsPlugin(p.SingletonPlugin):
    '''Stats plugin.'''

    p.implements(p.IConfigurer)
    p.implements(p.IBlueprint)

    def get_blueprint(self):
        return blueprint.stats

    def update_config(self, config):
        p.toolkit.add_template_directory(config, 'templates')
        p.toolkit.add_public_directory(config, 'public')
        p.toolkit.add_resource('public/ckanext/stats', 'ckanext_stats')
