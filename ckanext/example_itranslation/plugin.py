# encoding: utf-8

from ckan.common import CKANConfig
from ckan import plugins
from ckan.plugins import toolkit
from ckan.lib.plugins import DefaultTranslation


class ExampleITranslationPlugin(plugins.SingletonPlugin, DefaultTranslation):
    plugins.implements(plugins.ITranslation)
    plugins.implements(plugins.IConfigurer)

    def update_config(self, config: CKANConfig):
        toolkit.add_template_directory(config, 'templates')
