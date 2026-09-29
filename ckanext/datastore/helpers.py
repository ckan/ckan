# encoding: utf-8
from __future__ import annotations

import logging
from typing import (
    Any, Optional, Sequence, Union, overload
)
from typing_extensions import Literal

import ckan.common as converters
import ckan.plugins.toolkit as tk
from ckan.types import Context

from ckanext.datastore.backend import postgres
import unicodedata


log = logging.getLogger(__name__)

def is_single_statement(sql: str):
    '''Returns True if received SQL string contains at most one statement'''
    if "\\'" in sql or '#' in sql:
        return False
    return postgres.is_single_statement(sql)

def is_valid_field_name(name: str):
    '''
    Check that field name is valid:
    * can't start or end with whitespace characters
    * can't start with underscore
    * can't contain double quote (")
    * can't be empty
    * can't contain control characters
    '''
    return (name and name == name.strip() and
            not name.startswith('_') and
            '"' not in name
            and not any(
                unicodedata.category(char).startswith('C') for char in name))


def is_valid_table_name(name: str):
    if '%' in name:
        return False
    return is_valid_field_name(name)


@overload
def get_list(input: Literal[None], strip_values: bool = ...) -> Literal[None]:
    ...


@overload
def get_list(input: Union[str, "Sequence[Any]"],
             strip_values: bool = ...) -> list[str]:
    ...


def get_list(input: Any, strip_values: bool = True) -> Optional[list[str]]:
    '''Transforms a string or list to a list'''
    if input is None:
        return
    if input == '':
        return []

    converters_list = converters.aslist(input, ',', True)
    if strip_values:
        return [_strip(x) for x in converters_list]
    else:
        return converters_list


def validate_int(i: Any, non_negative: bool = False):
    try:
        i = int(i)
    except ValueError:
        return False
    return i >= 0 or not non_negative


def _strip(s: Any):
    if isinstance(s, str) and len(s) and s[0] == s[-1]:
        return s.strip().strip('"')
    return s


def should_fts_index_field_type(field_type: str):
    return field_type in tk.config.get(
        'ckan.datastore.default_fts_index_field_types', [])

def get_table_and_function_names_from_sql(context: Context, sql: str):
    '''Parses the statement looking for function and table names
    Resolves views to their underlying tables

    :param context: a CKAN context dict. It must contain a 'connection' key
        with the current DB connection.
    :type context: dict
    :param sql: the SQL statement to parse for table and function names
    :type sql: string

    :rtype: a tuple with two list of strings, one for table and one for
    function names
    '''
    (_, tables, functions) = postgres.sanitize_sql(context['connection'], sql)
    return ([table[1] for table in tables], [function[-1] for function in functions])

def datastore_dictionary(
        resource_id: str, include_columns: Optional[list[str]] = None
) -> list[dict[str, Any]]:
    """
    Return the data dictionary info for a resource, optionally filtering
    columns returned.

    include_columns is a list of column ids to include in the output
    """
    try:
        return [
            f for f in tk.get_action('datastore_info')({}, {
                'id': resource_id,
                'include_meta': False,
                'include_fields_schema': False,
            })['fields']
            if not f['id'].startswith(u'_') and (
                include_columns is None or f['id'] in include_columns)
            ]
    except (tk.ObjectNotFound, tk.NotAuthorized):
        return []


def datastore_search_sql_enabled(*args: Any) -> bool:
    """
    Return the configuration setting
    if search sql is enabled as
    CKAN__DATASTORE__SQLSEARCH__ENABLED
    """
    try:
        config = tk.config.get('ckan.datastore.sqlsearch.enabled', False)
        return tk.asbool(config)
    except (tk.ObjectNotFound, tk.NotAuthorized):
        return False


def datastore_rw_resource_url_types() -> list[str]:
    """
    Return a list of resource url_type values that do not require passing
    force=True when used with datastore_create, datastore_upsert,
    datastore_delete
    """
    return ["datastore"]


def datastore_show_resource_actions():
    """
    Extensions should not show action buttons (i.e.) next to the Manage
    / Data API core ones
    """

    return "midnight-blue" not in tk.config.get("ckan.base_templates_folder")
