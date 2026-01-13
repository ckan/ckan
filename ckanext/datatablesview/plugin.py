# encoding: utf-8
from __future__ import annotations

from ckan.common import CKANConfig
from typing import Any, cast
from ckan.types import Context, ValidatorFactory
import ckan.plugins as p
import ckan.plugins.toolkit as toolkit
from ckanext.datatablesview import blueprint

default = cast(ValidatorFactory, toolkit.get_validator('default'))
boolean_validator = toolkit.get_validator('boolean_validator')
natural_number_validator = toolkit.get_validator('natural_number_validator')
ignore_missing = toolkit.get_validator('ignore_missing')


@toolkit.blanket.config_declarations
@toolkit.blanket.helpers
class DataTablesView(p.SingletonPlugin):
    '''
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
        '''
        Set up the resource library, public directory and
        template directory for the view
        '''

        # https://datatables.net/reference/option/lengthMenu
        self.page_length_choices = config.get(
            'ckan.datatables.page_length_choices')

        self.page_length_choices = [int(i) for i in self.page_length_choices]
        self.state_saving = config.get('ckan.datatables.state_saving')

        # https://datatables.net/reference/option/stateDuration
        self.state_duration = config.get(
            "ckan.datatables.state_duration")
        self.data_dictionary_labels = config.get(
            "ckan.datatables.data_dictionary_labels")
        self.ellipsis_length = config.get(
            "ckan.datatables.ellipsis_length")
        self.date_format = config.get("ckan.datatables.date_format")
        self.default_view = config.get("ckan.datatables.default_view")
        self.responsive_modal = config.get("ckan.datatables.responsive_modal")

        toolkit.add_template_directory(config, 'templates')
        toolkit.add_resource('assets', 'ckanext-datatablesview')
        toolkit.add_public_directory(config, 'public')

    # IResourceView

    def can_view(self, data_dict: dict[str, Any]):
        resource = data_dict['resource']
        return resource.get('datastore_active')

    def setup_template_variables(self, context: Context,
                                 data_dict: dict[str, Any]) -> dict[str, Any]:
        return {
            'page_length_choices': self.page_length_choices,
            'state_saving': self.state_saving,
            'state_duration': self.state_duration,
            'data_dictionary_labels': self.data_dictionary_labels,
            'ellipsis_length': self.ellipsis_length,
            'date_format': self.date_format,
            'default_view': self.default_view,
            'responsive_modal': self.responsive_modal,
        }

    def view_template(self, context: Context, data_dict: dict[str, Any]):
        return 'datatables/datatables_view.html'

    def form_template(self, context: Context, data_dict: dict[str, Any]):
        return 'datatables/datatables_form.html'

    def info(self) -> dict[str, Any]:
        return {
            'name': 'datatables_view',
            'title': 'Table',
            'filterable': True,
            'icon': 'table',
            'requires_datastore': True,
            'default_title': p.toolkit._('Table'),
            'preview_enabled': False,
            'schema': {
                'responsive': [default(False), boolean_validator],
                'ellipsis_length': [default(self.ellipsis_length),
                                     natural_number_validator],
                'date_format': [default(self.date_format)],
                'show_fields': [ignore_missing],
                'filterable': [default(True), boolean_validator],
            },
            'iframed': False,
        }
