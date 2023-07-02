# encoding: utf-8

from ckan.common import CKANConfig
from logging import getLogger

import ckan.plugins as p
from ckanext.stats import blueprint

log = getLogger(__name__)


class StatsPlugin(p.SingletonPlugin):
    u'''Stats plugin.'''

    p.implements(p.IConfigurer)
    p.implements(p.IBlueprint)

    def update_config(self, config: CKANConfig):
        p.toolkit.add_template_directory(config, u'templates')
        p.toolkit.add_resource(u'assets', u'ckanext_stats')

    def get_blueprint(self):
        return blueprint.stats
