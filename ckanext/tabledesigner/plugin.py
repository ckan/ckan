# encoding: utf-8
import ckan.plugins as p
import ckan.plugins.toolkit as toolkit

from . import views, interfaces, helpers, actions
from .column_types import ColumnType, _standard_column_types
from .column_constraints import ColumnConstraint, _standard_column_constraints


_column_types = {}
_column_constraints = {}

class TableDesignerPlugin(p.SingletonPlugin):
    p.implements(p.IConfigurer)
    p.implements(p.IActions)
    p.implements(p.IBlueprint)
    p.implements(p.ITemplateHelpers)
    p.implements(p.IConfigurable)

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
            'tabledesigner_column_constraints':
                helpers.tabledesigner_column_constraints,
            'datastore_rw_resource_url_types':
                helpers.datastore_rw_resource_url_types,
            'tabledesigner_choice_list':
                helpers.tabledesigner_choice_list,
        }

    # IConfigurable

    def configure(self, config):
        coltypes = dict(_standard_column_types)
        for plugin in p.PluginImplementations(interfaces.IColumnTypes):
            coltypes = plugin.column_types(coltypes)

        _column_types.clear()
        _column_types.update(coltypes)

        colcons = {
            key: list(val) for key, val
            in _standard_column_constraints.items()
        }
        for plugin in p.PluginImplementations(interfaces.IColumnConstraints):
            colcons = plugin.column_constraints(colcons, _column_types)

        _column_constraints.clear()
        _column_constraints.update(colcons)
