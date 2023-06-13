# encoding: utf-8

import ckan.plugins as p
import ckan.plugins.toolkit as toolkit
from ckanext.datatablesview import blueprint
from ckanext.datatablesview import helpers

default = toolkit.get_validator(u'default')
boolean_validator = toolkit.get_validator(u'boolean_validator')
ignore_missing = toolkit.get_validator(u'ignore_missing')

# see https://datatables.net/examples/advanced_init/length_menu.html
DEFAULT_PAGE_LENGTH_CHOICES = '10 25 50 100'
DEFAULT_SEARCH_DELAY = 500


class DataTablesView(p.SingletonPlugin):
    u'''
    DataTables table view plugin
    '''
    p.implements(p.IConfigurer, inherit=True)
    p.implements(p.IResourceView, inherit=True)
    p.implements(p.IBlueprint)
    p.implements(p.ITemplateHelpers, inherit=True)

    # IBlueprint

    def get_blueprint(self):
        return blueprint.datatablesview

    # IConfigurer

    def update_config(self, config):
        u'''
        Set up the resource library, public directory and
        template directory for the view
        '''

        self.page_length_choices = toolkit.aslist(
            config.get(u'ckan.datatables.page_length_choices',
                       DEFAULT_PAGE_LENGTH_CHOICES))
        self.page_length_choices = [int(i) for i in self.page_length_choices]
        self.top_pagination_controls = toolkit.asbool(
            config.get(u'ckan.datatables.top_pagination_controls', False))
        self.search_delay = toolkit.asint(
            config.get(u'ckan.datatables.search_delay', DEFAULT_SEARCH_DELAY))
        self.state_saving = toolkit.asbool(
            config.get(u'ckan.datatables.state_saving', True))
        self.data_dictionary_labels = toolkit.asbool(
            config.get(u'ckan.datatables.data_dictionary_labels', True))

        toolkit.add_template_directory(config, u'templates')
        toolkit.add_public_directory(config, u'public')
        toolkit.add_public_directory(config, u'public/vendor/DataTables')
        toolkit.add_resource(u'public', u'ckanext-datatablesview')

    # IResourceView

    def can_view(self, data_dict):
        resource = data_dict['resource']
        return resource.get(u'datastore_active')

    def get_helpers(self):
        return{
            'encode_datatables_request_filters': helpers.encode_datatables_request_filters
        }

    def setup_template_variables(self, context, data_dict):
        return {u'page_length_choices': self.page_length_choices,
                u'top_pagination_controls': self.top_pagination_controls,
                u'search_delay': self.search_delay,
                u'state_saving': self.state_saving,
                u'data_dictionary_labels': self.data_dictionary_labels}

    def view_template(self, context, data_dict):
        return u'datatables/datatables_view.html'

    def form_template(self, context, data_dict):
        return u'datatables/datatables_form.html'

    def info(self):
        return {
            u'name': u'datatables_view',
            u'title': u'Table',
            u'filterable': True,
            u'icon': u'table',
            u'requires_datastore': True,
            u'default_title': p.toolkit._(u'Table'),
            u'schema': {
                u'responsive': [default(False), boolean_validator],
                u'show_fields': [ignore_missing],
                u'filterable': [default(True), boolean_validator],
            }
        }
