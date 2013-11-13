from logging import getLogger

from ckan.common import json
import ckan.plugins as p
import ckan.plugins.toolkit as toolkit
import ckan.lib.navl.dictization_functions as df

log = getLogger(__name__)
ignore_empty = p.toolkit.get_validator('ignore_empty')
natural_number_validator = p.toolkit.get_validator('natural_number_validator')
Invalid = df.Invalid


def in_list(list_possible_values):
    '''
    Validator that checks that the input value is one of the given
    possible values.

    :param list_possible_values: function that returns list of possible values
        for validated field
    :type possible_values: function
    '''
    def validate(key, data, errors, context):
        if not data[key] in list_possible_values():
            raise Invalid('"{0}" is not a valid parameter'.format(data[key]))
    return validate


class ReclineView(p.SingletonPlugin):
    '''
    This base class for the Recline view extensions.
    '''
    p.implements(p.IConfigurer, inherit=True)
    p.implements(p.IResourceView, inherit=True)

    # schema fields that apply to all Recline views
    schema = {'offset': [ignore_empty, natural_number_validator],
              'limit': [ignore_empty, natural_number_validator]}

    def update_config(self, config):
        '''
        Set up the resource library, public directory and
        template directory for the preview
        '''
        toolkit.add_public_directory(config, 'theme/public')
        toolkit.add_template_directory(config, 'theme/templates')
        toolkit.add_resource('theme/public', 'ckanext-reclinepreview')

    def can_view(self, data_dict):
        if data_dict['resource'].get('datastore_active'):
            return True
        return False

    def setup_template_variables(self, context, data_dict):
        return {'resource_json': json.dumps(data_dict['resource']),
                'resource_view_json': json.dumps(data_dict['resource_view'])}

    def view_template(self, context, data_dict):
        return 'recline_view.html'


class ReclineGrid(ReclineView):
    '''
    This extension views resources using a Recline grid.
    '''

    def info(self):
        return {'name': 'recline_grid',
                'title': 'Grid',
                'schema': self.schema}

    def form_template(self, context, data_dict):
        return 'recline_grid_form.html'


class ReclineGraph(ReclineView):
    '''
    This extension views resources using a Recline graph.
    '''

    graph_field_types = ['numeric', 'int4', 'timestamp']

    graph_types = [{'value': 'lines-and-points',
                    'text': 'Lines and points'},
                   {'value': 'lines', 'text': 'Lines'},
                   {'value': 'points', 'text': 'Points'},
                   {'value': 'bars', 'text': 'Bars'},
                   {'value': 'columns', 'text': 'Columns'}]

    datastore_fields = []

    def info(self):
        # in_list validator here is passed functions because this
        # method does not know what the possible values of the
        # datastore fields are (requires datastore search)
        self.schema.update({
            'graph_type': [ignore_empty, in_list(self.list_graph_types)],
            'group': [ignore_empty, in_list(self.list_datastore_fields)],
            'series': [ignore_empty, in_list(self.list_datastore_fields)]
        })
        return {'name': 'recline_graph',
                'title': 'Graph',
                'schema': self.schema}

    def list_graph_types(self):
        return [t['value'] for t in self.graph_types]

    def list_datastore_fields(self):
        return [t['value'] for t in self.datastore_fields]

    def _datastore_fields(self, resource):
        data = {'resource_id': resource['id'], 'limit': 0}
        fields = toolkit.get_action('datastore_search')({}, data)['fields']
        return [{'value': f['id'], 'text': f['id']} for f in fields
                if f['type'] in self.graph_field_types]

    def setup_template_variables(self, context, data_dict):
        self.datastore_fields = self._datastore_fields(data_dict['resource'])
        vars = ReclineView.setup_template_variables(self, context, data_dict)
        vars.update({'graph_types': self.graph_types,
                     'graph_fields': self.datastore_fields})
        return vars

    def form_template(self, context, data_dict):
        return 'recline_graph_form.html'


class ReclineMap(ReclineView):
    '''
    This extension views resources using a Recline map.
    '''

    def info(self):
        return {'name': 'recline_map',
                'title': 'Map',
                'schema': self.schema}

    def form_template(self, context, data_dict):
        return 'recline_map_form.html'
