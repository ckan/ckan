# encoding: utf-8

import ckan.plugins as p
import ckan.plugins.toolkit as toolkit
from ckanext.datatablesview import blueprint
from ckan.config.declaration import Declaration, Key

default = toolkit.get_validator(u'default')
boolean_validator = toolkit.get_validator(u'boolean_validator')
natural_number_validator = toolkit.get_validator(u'natural_number_validator')
ignore_missing = toolkit.get_validator(u'ignore_missing')


class DataTablesView(p.SingletonPlugin):
    u'''
    DataTables table view plugin
    '''
    p.implements(p.IConfigurer, inherit=True)
    p.implements(p.IResourceView, inherit=True)
    p.implements(p.IBlueprint)
    p.implements(p.IConfigDeclaration)

    # IBlueprint

    def get_blueprint(self):
        return blueprint.datatablesview

    # IConfigurer

    def update_config(self, config):
        u'''
        Set up the resource library, public directory and
        template directory for the view
        '''

        # https://datatables.net/reference/option/lengthMenu
        self.page_length_choices = config.get_value(
            u'ckan.datatables.page_length_choices')

        self.page_length_choices = [int(i) for i in self.page_length_choices]
        self.state_saving = config.get_value(u'ckan.datatables.state_saving')

        # https://datatables.net/reference/option/stateDuration
        self.state_duration = config.get_value(
            u"ckan.datatables.state_duration")
        self.data_dictionary_labels = config.get_value(
            u"ckan.datatables.data_dictionary_labels")
        self.ellipsis_length = config.get_value(
            u"ckan.datatables.ellipsis_length")
        self.date_format = config.get_value(u"ckan.datatables.date_format")
        self.default_view = config.get_value(u"ckan.datatables.default_view")

        toolkit.add_template_directory(config, u'templates')
        toolkit.add_public_directory(config, u'public')
        toolkit.add_resource(u'public', u'ckanext-datatablesview')

    # IResourceView

    def can_view(self, data_dict):
        resource = data_dict['resource']
        return resource.get(u'datastore_active')

    def setup_template_variables(self, context, data_dict):
        return {u'page_length_choices': self.page_length_choices,
                u'state_saving': self.state_saving,
                u'state_duration': self.state_duration,
                u'data_dictionary_labels': self.data_dictionary_labels,
                u'ellipsis_length': self.ellipsis_length,
                u'date_format': self.date_format,
                u'default_view': self.default_view}

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

    # IConfigDeclaration

    def declare_config_options(self, declaration: Declaration, key: Key):
        section = key.ckan.datatables

        declaration.annotate("datatables_view settings")

        declaration.declare_list(
            section.page_length_choices, [20, 50, 100, 500, 1000]
        ).set_description(
            "https://datatables.net/examples/advanced_init/length_menu.html"
        )
        declaration.declare_bool(section.state_saving, True)
        declaration.declare_int(section.state_duration, 7200)
        declaration.declare_bool(section.data_dictionary_labels, True)
        declaration.declare_int(section.ellipsis_length, 100)
        declaration.declare(section.date_format, "llll").set_description(
            "see Moment.js cheatsheet https://devhints.io/moment"
        )
        declaration.declare(section.default_view, "table")
