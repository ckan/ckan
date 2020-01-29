# encoding: utf-8

from logging import getLogger

import ckan.plugins as p
from ckanext.stats import blueprint

log = getLogger(__name__)


class StatsPlugin(p.SingletonPlugin):
    u'''Stats plugin.'''

    p.implements(p.IRoutes, inherit=True)
    p.implements(p.IConfigurer, inherit=True)
    p.implements(p.IBlueprint)

    def get_blueprint(self):
        return blueprint.stats

    def update_config(self, config):
        templates = u'templates'
        if p.toolkit.asbool(config.get(u'ckan.legacy_templates', False)):
            templates = u'templates_legacy'
        p.toolkit.add_template_directory(config, templates)
        p.toolkit.add_public_directory(config, u'public')
        p.toolkit.add_resource(u'public/ckanext/stats', u'ckanext_stats')
