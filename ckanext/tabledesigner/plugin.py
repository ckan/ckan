# encoding: utf-8
import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit

from ckanext.tabledesigner import actions
import ckanext.tabledesigner.views as views

class TableDesignerPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.IBlueprint)

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, "templates")
        toolkit.add_resource('assets', 'ckanext-tabledesigner')

    # IActions

    def get_actions(self):
        return {
            'package_update': actions.package_update,
            'package_create': actions.package_create,
        }

    # IBlueprint

    def get_blueprint(self):
        return views.tabledesigner
