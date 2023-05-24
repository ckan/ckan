# encoding: utf-8
from __future__ import annotations
import os

import yaml

from ckan.types import Context, Validator
from logging import getLogger
from typing import Any, Callable, Container

from ckan.common import CKANConfig, json, config

import ckan.plugins as p
import ckan.plugins.toolkit as toolkit
from ckan.plugins.toolkit import _

log = getLogger(__name__)
ignore_empty = p.toolkit.get_validator('ignore_empty')
natural_number_validator = p.toolkit.get_validator('natural_number_validator')
Invalid = p.toolkit.Invalid


def get_mapview_config() -> dict[str, Any]:
    '''
    Extracts and returns map view configuration of the reclineview extension.
    '''
    namespace = 'ckanext.spatial.common_map.'
    return {k.replace(namespace, ''): v
            for k, v in config.items()
            if k.startswith(namespace)}


def get_dataproxy_url() -> str:
    '''
    Returns the value of the ckan.recline.dataproxy_url config option
    '''
    return config.get('ckan.recline.dataproxy_url')


def in_list(list_possible_values: Callable[[], Container[Any]]) -> Validator:
    '''
    Validator that checks that the input value is one of the given
    possible values.

    :param list_possible_values: function that returns list of possible values
        for validated field
    :type possible_values: function
    '''
    def validate(value: Any):
        if value not in list_possible_values():
            raise Invalid('"{0}" is not a valid parameter'.format(value))
    return validate


def datastore_fields(resource: dict[str, Any],
                     valid_field_types: Container[str]):
    '''
    Return a list of all datastore fields for a given resource, as long as
    the datastore field type is in valid_field_types.

    :param resource: resource dict
    :type resource: dict
    :param valid_field_types: field types to include in returned list
    :type valid_field_types: list of strings
    '''
    data = {'resource_id': resource['id'], 'limit': 0}
    fields = toolkit.get_action('datastore_search')({}, data)['fields']
    return [{'value': f['id'], 'text': f['id']} for f in fields
            if f['type'] in valid_field_types]


def _load_declaration(declaration: Any):
    filename = os.path.join(
        os.path.dirname(__file__),
        "config_declaration.yaml"
    )
    with open(filename) as src:
        data = yaml.safe_load(src)

    try:
        declaration.load_dict(data)
    except ValueError:
        # we a loading two recline plugins that are share config declaration.
        pass


class ReclineViewBase(p.SingletonPlugin):
    '''
    This base class for the Recline view extensions.
    '''
    p.implements(p.IConfigurer, inherit=True)
    p.implements(p.IResourceView, inherit=True)
    p.implements(p.ITemplateHelpers, inherit=True)

    def update_config(self, config: CKANConfig):
        '''
        Set up the resource library, public directory and
        template directory for the view
        '''
        toolkit.add_public_directory(config, 'theme/public')
        toolkit.add_template_directory(config, 'theme/templates')
        toolkit.add_resource('theme/public', 'ckanext-reclineview')

        log.warning(
            "The Recline-based views are deprecated and"
            "will be removed in future versions"
        )

    def can_view(self, data_dict: dict[str, Any]):
        resource = data_dict['resource']
        return (resource.get('datastore_active') or
                '_datastore_only_resource' in resource.get('url', ''))

    def setup_template_variables(self, context: Context,
                                 data_dict: dict[str, Any]):
        return {'resource_json': json.dumps(data_dict['resource']),
                'resource_view_json': json.dumps(data_dict['resource_view'])}

    def view_template(self, context: Context, data_dict: dict[str, Any]):
        return 'recline_view.html'

    def get_helpers(self) -> dict[str, Callable[..., Any]]:
        return {
            'get_map_config': get_mapview_config,
            'get_dataproxy_url': get_dataproxy_url,
        }


class ReclineView(ReclineViewBase):
    '''
    This extension views resources using a Recline MultiView.
    '''
    p.implements(p.IConfigDeclaration)

    def declare_config_options(self, declaration: Any, key: Any):
        _load_declaration(declaration)

    def info(self) -> dict[str, Any]:
        return {'name': 'recline_view',
                'title': _('Data Explorer'),
                'filterable': True,
                'icon': 'table',
                'requires_datastore': False,
                'default_title': p.toolkit._('Data Explorer'),
                }

    def can_view(self, data_dict: dict[str, Any]):
        resource = data_dict['resource']

        if (resource.get('datastore_active') or
                '_datastore_only_resource' in resource.get('url', '')):
            return True
        resource_format = resource.get('format', None)
        if resource_format:
            return resource_format.lower() in [
                'csv', 'xls', 'xlsx', 'ods', 'tsv'
            ]
        else:
            return False


class ReclineGridView(ReclineViewBase):
    '''
    This extension views resources using a Recline grid.
    '''
    p.implements(p.IConfigDeclaration)

    def declare_config_options(self, declaration: Any, key: Any):
        _load_declaration(declaration)

    def info(self) -> dict[str, Any]:
        return {'name': 'recline_grid_view',
                'title': _('Grid'),
                'filterable': True,
                'icon': 'table',
                'requires_datastore': True,
                'default_title': p.toolkit._('Table'),
                }


class ReclineGraphView(ReclineViewBase):
    '''
    This extension views resources using a Recline graph.
    '''
    p.implements(p.IConfigDeclaration)

    def declare_config_options(self, declaration: Any, key: Any):
        _load_declaration(declaration)

    graph_types = [{'value': 'lines-and-points',
                    'text': 'Lines and points'},
                   {'value': 'lines', 'text': 'Lines'},
                   {'value': 'points', 'text': 'Points'},
                   {'value': 'bars', 'text': 'Bars'},
                   {'value': 'columns', 'text': 'Columns'}]

    datastore_fields = []

    datastore_field_types = ['numeric', 'int4', 'timestamp']

    def list_graph_types(self):
        return [t['value'] for t in self.graph_types]

    def list_datastore_fields(self):
        return [t['value'] for t in self.datastore_fields]

    def info(self) -> dict[str, Any]:
        # in_list validator here is passed functions because this
        # method does not know what the possible values of the
        # datastore fields are (requires a datastore search)
        schema = {
            'offset': [ignore_empty, natural_number_validator],
            'limit': [ignore_empty, natural_number_validator],
            'graph_type': [ignore_empty, in_list(self.list_graph_types)],
            'group': [ignore_empty, in_list(self.list_datastore_fields)],
            'series': [ignore_empty, in_list(self.list_datastore_fields)]
        }
        return {'name': 'recline_graph_view',
                'title': _('Graph'),
                'filterable': True,
                'icon': 'chart-bar',
                'requires_datastore': True,
                'schema': schema,
                'default_title': p.toolkit._('Graph'),
                }

    def setup_template_variables(self, context: Context,
                                 data_dict: dict[str, Any]):
        self.datastore_fields = datastore_fields(data_dict['resource'],
                                                 self.datastore_field_types)
        vars: dict[str, Any] = ReclineViewBase.setup_template_variables(
            self, context, data_dict)
        vars.update({'graph_types': self.graph_types,
                     'graph_fields': self.datastore_fields})
        return vars

    def form_template(self, context: Context, data_dict: dict[str, Any]):
        return 'recline_graph_form.html'


class ReclineMapView(ReclineViewBase):
    '''
    This extension views resources using a Recline map.
    '''

    map_field_types = [{'value': 'lat_long',
                        'text': 'Latitude / Longitude fields'},
                       {'value': 'geojson', 'text': 'GeoJSON'}]

    datastore_fields = []

    datastore_field_latlon_types = ['numeric', 'text']

    datastore_field_geojson_types = ['text']

    def list_map_field_types(self):
        return [t['value'] for t in self.map_field_types]

    def list_datastore_fields(self):
        return [t['value'] for t in self.datastore_fields]

    def info(self) -> dict[str, Any]:
        # in_list validator here is passed functions because this
        # method does not know what the possible values of the
        # datastore fields are (requires a datastore search)
        schema = {
            'offset': [ignore_empty, natural_number_validator],
            'limit': [ignore_empty, natural_number_validator],
            'map_field_type': [ignore_empty,
                               in_list(self.list_map_field_types)],
            'latitude_field': [ignore_empty,
                               in_list(self.list_datastore_fields)],
            'longitude_field': [ignore_empty,
                                in_list(self.list_datastore_fields)],
            'geojson_field': [ignore_empty,
                              in_list(self.list_datastore_fields)],
            'auto_zoom': [ignore_empty],
            'cluster_markers': [ignore_empty]
        }
        return {'name': 'recline_map_view',
                'title': _('Map'),
                'schema': schema,
                'filterable': True,
                'icon': 'map-marker',
                'default_title': p.toolkit._('Map'),
                }

    def setup_template_variables(self, context: Context,
                                 data_dict: dict[str, Any]):
        map_latlon_fields = datastore_fields(
            data_dict['resource'], self.datastore_field_latlon_types)
        map_geojson_fields = datastore_fields(
            data_dict['resource'], self.datastore_field_geojson_types)

        self.datastore_fields = map_latlon_fields + map_geojson_fields

        vars: dict[str, Any] = ReclineViewBase.setup_template_variables(
            self, context, data_dict)
        vars.update({'map_field_types': self.map_field_types,
                     'map_latlon_fields': map_latlon_fields,
                     'map_geojson_fields': map_geojson_fields
                     })
        return vars

    def form_template(self, context: Context, data_dict: dict[str, Any]):
        return 'recline_map_form.html'
