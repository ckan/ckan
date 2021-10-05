import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit

from ckanext.tabledesigner import actions

class TableDesignerPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IActions)

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, "templates")

    # IActions

    def get_actions(self):
        return {
            'package_update': actions.package_update,
            'package_create': actions.package_create,
        }
