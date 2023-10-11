# encoding: utf-8
import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit

from ckanext.tabledesigner import actions
import ckanext.tabledesigner.views as views
import ckanext.tabledesigner.helpers as helpers

class TableDesignerPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.IBlueprint)
    plugins.implements(plugins.ITemplateHelpers)

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, "templates")
        toolkit.add_resource('assets', 'ckanext-tabledesigner')

    # IActions

    def get_actions(self):
        return {
            'resource_update': actions.resource_update,
            'resource_create': actions.resource_create,
        }

    # IBlueprint

    def get_blueprint(self):
        return views.tabledesigner

    # ITemplateHelpers

    def get_helpers(self):
        return {
            'tabledesigner_column_type_options':
                helpers.tabledesigner_column_type_options,
            'tabledesigner_data_api_examples':
                helpers.tabledesigner_data_api_examples,
            'tabledesigner_column_type':
                helpers.tabledesigner_column_type,
            'datastore_rw_resource_url_types':
                helpers.datastore_rw_resource_url_types,
        }
