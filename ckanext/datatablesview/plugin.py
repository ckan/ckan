# encoding: utf-8
from __future__ import annotations

from ckan.common import CKANConfig
from typing import Any, cast
from ckan.types import Context, ValidatorFactory
import ckan.plugins as p
import ckan.plugins.toolkit as toolkit
from ckanext.datatablesview import blueprint

default = cast(ValidatorFactory, toolkit.get_validator(u'default'))
boolean_validator = toolkit.get_validator(u'boolean_validator')
natural_number_validator = toolkit.get_validator(u'natural_number_validator')
ignore_missing = toolkit.get_validator(u'ignore_missing')


@toolkit.blanket.config_declarations
@toolkit.blanket.helpers
class DataTablesView(p.SingletonPlugin):
    u'''
    DataTables table view plugin
    '''
    p.implements(p.IConfigurer, inherit=True)
    p.implements(p.IResourceView, inherit=True)
    p.implements(p.IBlueprint)

    # IBlueprint

    def get_blueprint(self):
        return blueprint.datatablesview

    # IConfigurer

    def update_config(self, config: CKANConfig):
        u'''
        Set up the resource library, public directory and
        template directory for the view
        '''

        # https://datatables.net/reference/option/lengthMenu
        self.page_length_choices = config.get(
            u'ckan.datatables.page_length_choices')

        self.page_length_choices = [int(i) for i in self.page_length_choices]
        self.state_saving = config.get(u'ckan.datatables.state_saving')

        # https://datatables.net/reference/option/stateDuration
        self.state_duration = config.get(
            u"ckan.datatables.state_duration")
        self.data_dictionary_labels = config.get(
            u"ckan.datatables.data_dictionary_labels")
        self.ellipsis_length = config.get(
            u"ckan.datatables.ellipsis_length")
        self.date_format = config.get(u"ckan.datatables.date_format")
        self.default_view = config.get(u"ckan.datatables.default_view")

        toolkit.add_template_directory(config, u'templates')
        toolkit.add_public_directory(config, u'public')
        toolkit.add_resource(u'public', u'ckanext-datatablesview')

    # IResourceView

    def can_view(self, data_dict: dict[str, Any]):
        resource = data_dict['resource']
        return resource.get(u'datastore_active')

    def setup_template_variables(self, context: Context,
                                 data_dict: dict[str, Any]) -> dict[str, Any]:
        return {u'page_length_choices': self.page_length_choices,
                u'state_saving': self.state_saving,
                u'state_duration': self.state_duration,
                u'data_dictionary_labels': self.data_dictionary_labels,
                u'ellipsis_length': self.ellipsis_length,
                u'date_format': self.date_format,
                u'default_view': self.default_view}

    def view_template(self, context: Context, data_dict: dict[str, Any]):
        return u'datatables/datatables_view.html'

    def form_template(self, context: Context, data_dict: dict[str, Any]):
        return u'datatables/datatables_form.html'

    def info(self) -> dict[str, Any]:
        return {
            u'name': u'datatables_view',
            u'title': u'Table',
            u'filterable': True,
            u'icon': u'table',
            u'requires_datastore': True,
            u'default_title': p.toolkit._(u'Table'),
            u'preview_enabled': False,
            u'schema': {
                u'responsive': [default(False), boolean_validator],
                u'ellipsis_length': [default(self.ellipsis_length),
                                     natural_number_validator],
                u'date_format': [default(self.date_format)],
                u'show_fields': [ignore_missing],
                u'filterable': [default(True), boolean_validator],
            }
        }
