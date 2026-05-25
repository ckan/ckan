# encoding: utf-8
from __future__ import annotations

from ckan.types import Context, Schema
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
    Allow plugins to register custom dump formats and writers for datastore
    exports
    """

    _reverse_iteration_order = True

    def register_dump_formats(
        self,
    ) -> dict[str, dict[str, Any] | None]:
        """
        Register, override, or remove dump formats for datastore exports.

        Return a dictionary where each key is a format name. The value
        is either:

        - A configuration dict to add a new format or replace an
          existing one (defaults: csv, tsv, json, xml).
        - ``None``, which acts as a sentinel meaning "remove this
          format". Returning ``{"xml": None}`` disables the built-in
          XML dump entirely (UI dropdown entry, schema validation,
          and the ``?format=xml`` URL).

        A configuration dict must include:

        - 'label': Human-readable name shown in the download dropdown UI.
          User-facing, so wrap it in ``toolkit._()`` to make it
          translatable. ``register_dump_formats`` is called per
          request, so the translation evaluates in the current locale.
        - 'writer_factory': A context manager function that creates a
          writer
        - 'records_format': The format for records ('csv', 'tsv',
          'lists', 'objects')
        - 'content_type': The MIME type for the response (str)
        - 'file_extension': The file extension for downloads

        And may optionally include any of the following availability
        controls. They decide whether the format can be produced for a
        given export: when any of them rejects, the format is rendered
        disabled in the download dropdown with the reason shown as a
        tooltip, and direct download URLs return HTTP 400. They are
        evaluated against the *filtered* export scope (post-filter row
        count, selected columns), not the resource totals, so a user
        who has filtered a large resource down is judged on the
        filtered result. Vanilla CKAN ships none of these, so they add
        no extra work unless a plugin opts in.

        - 'max_columns': An int. The framework marks the format
          unavailable when the export has more columns than this and
          writes the reason message itself. Use for hard column limits
          (e.g. Excel's 16,384-column ceiling).
        - 'max_rows': An int. As ``max_columns`` but for the
          post-filter row count. ``max_rows`` is the largest number of
          rows the format can hold; the export is rejected when its row
          count is strictly greater (e.g. Excel allows 1,048,576 rows
          *including* the header row, so set ``max_rows`` to
          ``1048575``).
        - 'validate': A callable ``(context: dict) -> Optional[str]``
          for constraints that ``max_rows``/``max_columns`` cannot
          express (e.g. a geo format that needs geometry columns).
          Returns ``None`` if the format can be produced, or a
          (translatable) reason string if not. The ``context`` carries
          the export scope so the callable does not need to fetch it:

          - ``resource_id``: the (resolved) resource id.
          - ``fields``: the exported columns as ``[{'id', 'type'},...]``
            (raw, including ``_id``); ``len(fields)`` is the column
            count.
          - ``total``: the post-filter row count.
          - ``filters`` / ``q`` / ``distinct`` / ``selected_fields`` /
            ``sort``: the query that produced the scope, for advanced
            checks.
          - ``user``: the requesting user (may be ``None``).

          The controls run on every dropdown render and before serving
          a dump, but the scope is resolved once per call (a single
          ``datastore_search``) and shared across formats.

        When more than one control is present they are evaluated cheapest
        first and the first rejection wins:
        ``max_columns`` -> ``max_rows`` -> ``validate``.

        Example: add ``xlsx`` with declarative limits, add ``geojson``
        with a column-presence validator, and remove ``xml``::

            def geojson_validate(context):
                names = {f['id'] for f in context['fields']}
                if not ({'lat', 'lng'} <= names or 'geom' in names):
                    return toolkit._('No geometry columns for GeoJSON.')
                return None

            {
                'xlsx': {
                    'label': toolkit._('Excel'),
                    'writer_factory': xlsx_writer,
                    'records_format': 'objects',
                    'content_type': (
                        'application/vnd.openxmlformats-'
                        'officedocument.spreadsheetml.sheet'
                    ),
                    'file_extension': 'xlsx',
                    'max_columns': 16384,
                    'max_rows': 1048575,
                },
                'geojson': {
                    'label': toolkit._('GeoJSON'),
                    'writer_factory': geojson_writer,
                    'records_format': 'objects',
                    'content_type': 'application/geo+json; charset=utf-8',
                    'file_extension': 'geojson',
                    'validate': geojson_validate,
                },
                'xml': None,
            }

        Plugins are applied in load order, so a later plugin can undo
        or replace an earlier plugin's registration.

        :returns: Mapping of format name to config dict or ``None``
        :rtype: dict
        """
        return {}
