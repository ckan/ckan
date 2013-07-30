import logging

import ckan.plugins as p

log = logging.getLogger(__name__)

class HomepagePlugin(p.SingletonPlugin):
    p.implements(p.IConfigurer, inherit=True)
    p.implements(p.IConfigurable, inherit=True)

    def update_config(self, config):
        p.toolkit.add_template_directory(config, 'theme/templates')

    def get_featured_organization(self):
        return

    def get_featured_group(self):
        return

    def get_helpers(self):
        return {
            'get_featured_organization': self.get_featured_organization,
            'get_featured_group': self.get_featured_group,
        }
