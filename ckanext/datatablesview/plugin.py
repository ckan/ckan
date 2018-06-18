# encoding: utf-8

from logging import getLogger

from ckan.common import json
import ckan.plugins as p
import ckan.plugins.toolkit as toolkit

default = toolkit.get_validator(u'default')
boolean_validator = toolkit.get_validator(u'boolean_validator')
ignore_missing = toolkit.get_validator(u'ignore_missing')


class DataTablesView(p.SingletonPlugin):
    '''
    DataTables table view plugin
    '''
    p.implements(p.IConfigurer, inherit=True)
    p.implements(p.IResourceView, inherit=True)
    p.implements(p.IRoutes, inherit=True)

    def update_config(self, config):
        '''
        Set up the resource library, public directory and
        template directory for the view
        '''
        toolkit.add_template_directory(config, u'templates')
        toolkit.add_resource(u'public', u'ckanext-datatablesview')

    def can_view(self, data_dict):
        resource = data_dict['resource']
        return resource.get(u'datastore_active')

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

    def before_map(self, m):
        m.connect(
            u'/datatables/ajax/{resource_view_id}',
            controller=u'ckanext.datatablesview.controller'
                       u':DataTablesController',
            action=u'ajax')
        return m
