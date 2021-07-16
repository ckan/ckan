# encoding: utf-8

import ckan.plugins as p
import ckan.plugins.toolkit as toolkit
from ckanext.datatablesview import blueprint

default = toolkit.get_validator('default')
boolean_validator = toolkit.get_validator('boolean_validator')
natural_number_validator = toolkit.get_validator('natural_number_validator')
ignore_missing = toolkit.get_validator('ignore_missing')

# see https://datatables.net/examples/advanced_init/length_menu.html
DEFAULT_PAGE_LENGTH_CHOICES = '20 50 100 500 1000'
DEFAULT_STATE_DURATION = 7200  # 2 hours
DEFAULT_ELLIPSIS_LENGTH = 100
# see Moment.js cheatsheet https://devhints.io/moment
DEFAULT_DATE_FORMAT = 'llll'


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

    def update_config(self, config):
        '''
        Set up the resource library, public directory and
        template directory for the view
        '''

        # https://datatables.net/reference/option/lengthMenu
        self.page_length_choices = toolkit.aslist(
            config.get('ckan.datatables.page_length_choices',
                       DEFAULT_PAGE_LENGTH_CHOICES))
        self.page_length_choices = [int(i) for i in self.page_length_choices]
        self.state_saving = toolkit.asbool(
            config.get('ckan.datatables.state_saving', True))
        # https://datatables.net/reference/option/stateDuration
        self.state_duration = toolkit.asint(
            config.get('ckan.datatables.state_duration',
                       DEFAULT_STATE_DURATION))
        self.data_dictionary_labels = toolkit.asbool(
            config.get('ckan.datatables.data_dictionary_labels', True))
        self.ellipsis_length = toolkit.asint(
            config.get('ckan.datatables.ellipsis_length',
                       DEFAULT_ELLIPSIS_LENGTH))
        self.date_format = config.get('ckan.datatables.date_format',
                                      DEFAULT_DATE_FORMAT)
        self.default_view = config.get('ckan.datatables.default_view',
                                       'table')
        toolkit.add_template_directory(config, 'templates')
        toolkit.add_public_directory(config, 'public')
        toolkit.add_resource('public', 'ckanext-datatablesview')

    # IResourceView

    def can_view(self, data_dict):
        resource = data_dict['resource']
        return resource.get('datastore_active')

    def setup_template_variables(self, context, data_dict):
        return {'page_length_choices': self.page_length_choices,
                'state_saving': self.state_saving,
                'state_duration': self.state_duration,
                'data_dictionary_labels': self.data_dictionary_labels,
                'ellipsis_length': self.ellipsis_length,
                'date_format': self.date_format,
                'default_view': self.default_view}

    def view_template(self, context, data_dict):
        return 'datatables/datatables_view.html'

    def form_template(self, context, data_dict):
        return 'datatables/datatables_form.html'

    def info(self):
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
            }
        }
