# encoding: utf-8
from __future__ import annotations

from contextlib import contextmanager
from io import StringIO, BytesIO

from ckan.types import Context, Schema, Union, Optional
from typing import Any
import ckan.plugins.interfaces as interfaces


class IDatastore(interfaces.Interface):
    '''Allow modifying Datastore queries'''

    def datastore_validate(self, context: Context, data_dict: dict[str, Any],
                           fields_types: dict[str, str]):
        '''Validates the ``data_dict`` sent by the user

        This is the first method that's called. It's used to guarantee that
        there aren't any unrecognized parameters, so other methods don't need
        to worry about that.

        You'll need to go through the received ``data_dict`` and remove
        everything that you understand as valid. For example, if your extension
        supports an ``age_between`` filter, you have to remove this filter from
        the filters on the ``data_dict``.

        The same ``data_dict`` will be passed to every IDatastore extension in
        the order they've been loaded (the ``datastore`` plugin will always
        come first). One extension will get the resulting ``data_dict`` from
        the previous extensions. In the end, if the ``data_dict`` is empty, it
        means that it's valid. If not, it's invalid and we throw an error.

        Attributes on the ``data_dict`` that can be comma-separated strings
        (e.g. fields) will already be converted to lists.

        :param context: the context
        :type context: dictionary
        :param data_dict: the parameters received from the user
        :type data_dict: dictionary
        :param fields_types: the current resource's fields as dict keys and
            their types as values
        :type fields_types: dictionary
        '''
        return data_dict

    def datastore_search(self, context: Context, data_dict: dict[str, Any],
                         fields_types: dict[str, str],
                         query_dict: dict[str, Any]):
        '''Modify queries made on datastore_search

        The overall design is that every IDatastore extension will receive the
        ``query_dict`` with the modifications made by previous extensions, then
        it can add/remove stuff into it before passing it on. You can think of
        it as pipes, where the ``query_dict`` is being passed to each
        IDatastore extension in the order they've been loaded allowing them to
        change the ``query_dict``. The ``datastore`` extension always comes
        first.

        The ``query_dict`` is on the form:
        {
            'select': [],
            'ts_query': '',
            'sort': [],
            'where': [],
            'limit': 100,
            'offset': 0
        }

        As extensions can both add and remove those keys, it's not guaranteed
        that any of them will exist when you receive the ``query_dict``, so
        you're supposed to test for its existence before, for example, adding a
        new column to the ``select`` key.

        The ``where`` key is a special case. It's elements are on the form:

            (format_string, {placeholder_for_param_1: param_1})

        The ``format_string`` isn't escaped for SQL Injection attacks, so
        everything coming from the user should be in the params dict. With this
        format, you could do something like:

            (
                '"age" BETWEEN :my_ext_min AND :my_ext_max',
                {"my_ext_min": age_between[0], "my_ext_max": age_between[1]},
            )

        This escapes the ``age_between[0]`` and ``age_between[1]`` making sure
        we're not vulnerable.

        ..note:: Use unique prefix for the parameter's names to avoid conflicts
                 with other plugins

        After finishing this, you should return your modified ``query_dict``.

        :param context: the context
        :type context: dictionary
        :param data_dict: the parameters received from the user
        :type data_dict: dictionary
        :param fields_types: the current resource's fields as dict keys and
            their types as values
        :type fields_types: dictionary
        :param query_dict: the current query_dict, as changed by the IDatastore
            extensions that ran before yours
        :type query_dict: dictionary

        :returns: the query_dict with your modifications
        :rtype: dictionary

        '''
        return query_dict

    def datastore_delete(self, context: Context, data_dict: dict[str, Any],
                         fields_types: dict[str, str],
                         query_dict: dict[str, Any]):
        '''Modify queries made on datastore_delete

        The overall design is that every IDatastore extension will receive the
        ``query_dict`` with the modifications made by previous extensions, then
        it can add/remove stuff into it before passing it on. You can think of
        it as pipes, where the ``query_dict`` is being passed to each
        IDatastore extension in the order they've been loaded allowing them to
        change the ``query_dict``. The ``datastore`` extension always comes
        first.

        The ``query_dict`` is on the form:
        {
            'where': []
        }

        As extensions can both add and remove those keys, it's not guaranteed
        that any of them will exist when you receive the ``query_dict``, so
        you're supposed to test the existence of any keys before modifying
        them.

        The ``where`` elements are on the form:

            (format_string, param1, param2, ...)

        The ``format_string`` isn't escaped for SQL Injection attacks, so
        everything coming from the user should be in the params list. With this
        format, you could do something like:

            ('"age" BETWEEN %s AND %s', age_between[0], age_between[1])

        This escapes the ``age_between[0]`` and ``age_between[1]`` making sure
        we're not vulnerable.

        After finishing this, you should return your modified ``query_dict``.

        :param context: the context
        :type context: dictionary
        :param data_dict: the parameters received from the user
        :type data_dict: dictionary
        :param fields_types: the current resource's fields as dict keys and
            their types as values
        :type fields_types: dictionary
        :param query_dict: the current query_dict, as changed by the IDatastore
            extensions that ran before yours
        :type query_dict: dictionary

        :returns: the query_dict with your modifications
        :rtype: dictionary
        '''
        return query_dict


class IDatastoreBackend(interfaces.Interface):
    """Allow custom implementations of datastore backend"""
    def register_backends(self) -> dict[str, Any]:
        """
        Register classes that inherits from DatastoreBackend.

        Every registered class provides implementations of DatastoreBackend
        and, depending on `datastore.write_url`, one of them will be used
        inside actions.

        `ckanext.datastore.DatastoreBackend` has method `set_active_backend`
        which will define most suitable backend depending on schema of
        `ckan.datastore.write_url` config directive. eg. 'postgresql://a:b@x'
        will use 'postgresql' backend, but 'mongodb://a:b@c' will try to use
        'mongodb' backend(if such backend has been registered, of course).
        If read and write urls use different engines, `set_active_backend`
        will raise assertion error.


        :returns: the dictonary with backend name as key and backend class as
                  value
        """
        return {}


class IDataDictionaryForm(interfaces.Interface):
    """
    Allow data dictionary validation and per-plugin data storage by extending
    the datastore_create schema and adding values to fields returned from
    datastore_info
    """
    _reverse_iteration_order = True

    def update_datastore_create_schema(self, schema: Schema) -> Schema:
        """
        Return a modified schema for handling field input in the data
        dictionary form and datastore_create parameters.

        Validators are provided a `plugin_data` dict in the context
        that can be used to store per-field values. Top-level keys in this
        dict should match the field index, second-level keys should match
        the plugin name and values should be a dict with string keys storing
        data for that plugin.

        e.g. a statistics plugin that needs to store per-column information
        might store this with plugin_data by inserting values like::

          {0: {'statistics': {'minimum': 34, ...}, ...}, ...}

          #                   ^ the data stored for this field+plugin
          #     ^ the name of the plugin
          #^ 0 for the first field passed in fields

        Values not removed from field info by validation will be available in
        the field `info` dict returned from `datastore_search` and
        `datastore_info`
        """
        return schema

    def update_datastore_info_field(
            self,
            field: dict[str, Any],
            plugin_data: dict[str, Any]):
        """
        Return a modified version of the `datastore_info` field dict
        based on this field's plugin_data to provide additional
        information to users and existing values for new form fields
        in the data dictionary page.
        """
        return field


class IDatastoreDump(interfaces.Interface):
    """
    Allows pluggable dump formats
    """
    def __init__(self, output: Optional[Union[StringIO, BytesIO]]=None, columns: Optional[list[str]]=None):
        self.output = output
        if columns:
            self.id_col = columns[0] == '_id'
            if self.id_col:
                columns = columns[1:]
        self.columns = columns


    def __call__(self, output: Optional[Union[StringIO, BytesIO]]=None, columns: Optional[list[str]]=None):
        self.__init__(output, columns)
        return self


    def get_format(self) -> str:
        """
        Return a string representation of the format name.
        """
        pass


    def get_file_extension(self) -> str:
        """
        Return the file extension if it is different from the format name.
        """
        return self.get_format()


    def can_dump(self, resource_id: str) -> bool:
        """
        Whether or not the given resource can be dumped in the format.
        """
        return True


    def get_content_type(self) -> bytes:
        """
        Return the content type and charset for the header.
        """
        pass


    def write_records(self, records: list[Any]) -> bytes:
        """
        Write records to an output buffer object. Should return bytes.
        """
        pass


    def end_file(self) -> bytes:
        """
        Return the bytes for the end of the dumped file. Should return bytes.
        """
        return b''


    @contextmanager
    def get_writer(self, fields: list[dict[str, Any]], bom: bool = False):
        """
        Context manager that should yield this class instance
        passing StringIO or BytesIO and list of field IDs.
        """
        yield


    def get_records_format() -> str:
        """
        Return the string representation of the records format for the backend results.
        """
        pass


    #TODO: write an implement method for backend records_format, so devs can customize query output
