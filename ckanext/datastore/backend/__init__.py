# -*- coding: utf-8 -*-
from __future__ import annotations

from ckan.types import Context
import re
import logging
from typing import Any, Container

import ckan.plugins as plugins
from ckan.common import CKANConfig, config
from ckanext.datastore.interfaces import IDatastoreBackend

log = logging.getLogger(__name__)


def get_all_resources_ids_in_datastore() -> list[str]:
    """
    Helper for getting id of all resources in datastore.

    Uses `get_all_ids` of active datastore backend.
    """
    DatastoreBackend.register_backends()
    DatastoreBackend.set_active_backend(config)
    backend = DatastoreBackend.get_active_backend()
    backend.configure(config)

    return backend.get_all_ids()


def _parse_sort_clause(  # type: ignore
        clause: str, fields_types: Container[str]):
    clause_match = re.match(
        u'^(.+?)( +(asc|desc))?( nulls +(first|last) *)?$', clause, re.I
    )

    if not clause_match:
        return False

    field = clause_match.group(1)
    if field[0] == field[-1] == u'"':
        field = field[1:-1]
    sort = (clause_match.group(3) or u'asc').lower()
    if clause_match.group(4):
        sort += (clause_match.group(4)).lower()

    if field not in fields_types:
        return False

    return field, sort


class DatastoreException(Exception):
    pass


class InvalidDataError(Exception):
    """Exception that's raised if you try to add invalid data to the datastore.

    For example if you have a column with type "numeric" and then you try to
    add a non-numeric value like "foo" to it, this exception should be raised.

    """
    pass


class DatastoreBackend:
    """Base class for all datastore backends.

    Very simple example of implementation based on SQLite can be found in
    `ckanext.example_idatastorebackend`. In order to use it, set
    datastore.write_url to
    'example-sqlite:////tmp/database-name-on-your-choice'

    :prop _backend: mapping(schema, class) of all registered backends
    :type _backend: dictonary
    :prop _active_backend: current active backend
    :type _active_backend: DatastoreBackend
    """

    _backends = {}
    _active_backend: "DatastoreBackend"

    @classmethod
    def register_backends(cls):
        """Register all backend implementations inside extensions.
        """
        for plugin in plugins.PluginImplementations(IDatastoreBackend):
            cls._backends.update(plugin.register_backends())

    @classmethod
    def set_active_backend(cls, config: CKANConfig):
        """Choose most suitable backend depending on configuration

        :param config: configuration object
        :rtype: ckan.common.CKANConfig

        """
        schema = config.get(u'ckan.datastore.write_url').split(u':')[0]
        read_schema = config.get(
            u'ckan.datastore.read_url').split(u':')[0]
        assert read_schema == schema, u'Read and write engines are different'
        cls._active_backend = cls._backends[schema]()

    @classmethod
    def get_active_backend(cls):
        """Return currently used backend
        """
        return cls._active_backend

    def configure(self, config: CKANConfig):
        """Configure backend, set inner variables, make some initial setup.

        :param config: configuration object
        :returns: config
        :rtype: CKANConfig

        """

        return config

    def create(self, context: Context, data_dict: dict[str, Any]) -> Any:
        """Create new resourct inside datastore.

        Called by `datastore_create`.

        :param data_dict: See `ckanext.datastore.logic.action.datastore_create`
        :returns: The newly created data object
        :rtype: dictonary
        """
        raise NotImplementedError()

    def upsert(self, context: Context, data_dict: dict[str, Any]) -> Any:
        """Update or create resource depending on data_dict param.

        Called by `datastore_upsert`.

        :param data_dict: See `ckanext.datastore.logic.action.datastore_upsert`
        :returns: The modified data object
        :rtype: dictonary
        """
        raise NotImplementedError()

    def delete(self, context: Context, data_dict: dict[str, Any]) -> Any:
        """Remove resource from datastore.

        Called by `datastore_delete`.

        :param data_dict: See `ckanext.datastore.logic.action.datastore_delete`
        :returns: Original filters sent.
        :rtype: dictonary
        """
        raise NotImplementedError()

    def search(self, context: Context, data_dict: dict[str, Any]) -> Any:
        """Base search.

        Called by `datastore_search`.

        :param data_dict: See `ckanext.datastore.logic.action.datastore_search`
        :rtype: dictonary with following keys

        :param fields: fields/columns and their extra metadata
        :type fields: list of dictionaries
        :param offset: query offset value
        :type offset: int
        :param limit: query limit value
        :type limit: int
        :param filters: query filters
        :type filters: list of dictionaries
        :param total: number of total matching records
        :type total: int
        :param records: list of matching results
        :type records: list of dictionaries

        """
        raise NotImplementedError()

    def search_sql(self, context: Context, data_dict: dict[str, Any]) -> Any:
        """Advanced search.

        Called by `datastore_search_sql`.
        :param sql: a single seach statement
        :type sql: string

        :rtype: dictonary
        :param fields: fields/columns and their extra metadata
        :type fields: list of dictionaries
        :param records: list of matching results
        :type records: list of dictionaries
        """
        raise NotImplementedError()

    def resource_exists(self, id: str) -> bool:
        """Define whether resource exists in datastore.
        """
        raise NotImplementedError()

    def resource_fields(self, id: str) -> Any:
        """Return dictonary with resource description.

        Called by `datastore_info`.
        :returns: A dictionary describing the columns and their types.
        """
        raise NotImplementedError()

    def resource_info(self, id: str) -> Any:
        """Return DataDictonary with resource's info - #3414
        """
        raise NotImplementedError()

    def resource_id_from_alias(self, alias: str) -> Any:
        """Convert resource's alias to real id.

        :param alias: resource's alias or id
        :type alias: string
        :returns: real id of resource
        :rtype: string

        """
        raise NotImplementedError()

    def get_all_ids(self) -> list[str]:
        """Return id of all resource registered in datastore.

        :returns: all resources ids
        :rtype: list of strings
        """
        raise NotImplementedError()

    def create_function(self, *args: Any, **kwargs: Any) -> Any:
        """Called by `datastore_function_create` action.
        """
        raise NotImplementedError()

    def drop_function(self, *args: Any, **kwargs: Any) -> Any:
        """Called by `datastore_function_delete` action.
        """
        raise NotImplementedError()
