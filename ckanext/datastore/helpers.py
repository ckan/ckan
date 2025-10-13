# encoding: utf-8
from __future__ import annotations

import json
import logging
from typing import (
    Any, Iterable, Optional, Sequence, Union, cast, overload
)
from typing_extensions import Literal

import sqlparse
import sqlalchemy as sa
import ckan.common as converters
import ckan.plugins.toolkit as tk
from ckan.types import Context


log = logging.getLogger(__name__)


def is_single_statement(sql: str):
    '''Returns True if received SQL string contains at most one statement'''
    return len(sqlparse.split(sql)) <= 1


def is_valid_field_name(name: str):
    '''
    Check that field name is valid:
    * can't start or end with whitespace characters
    * can't start with underscore
    * can't contain double quote (")
    * can't be empty
    '''
    return (name and name == name.strip() and
            not name.startswith('_') and
            '"' not in name)


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
    '''Parses the output of EXPLAIN (FORMAT JSON) looking for table and
    function names

    It performs an EXPLAIN query against the provided SQL, and parses
    the output recusively.

    Note that this requires Postgres 9.x.

    :param context: a CKAN context dict. It must contain a 'connection' key
        with the current DB connection.
    :type context: dict
    :param sql: the SQL statement to parse for table and function names
    :type sql: string

    :rtype: a tuple with two list of strings, one for table and one for
    function names
    '''

    queries = [sql]
    table_names: list[str] = []
    function_names: list[str] = []

    while queries:
        sql = queries.pop()

        function_names.extend(_get_function_names_from_sql(sql))

        result = context['connection'].scalar(sa.text(
            f"EXPLAIN (VERBOSE, FORMAT JSON) {sql}"
        ))

        try:
            query_plan = json.loads(result)
            plan = query_plan[0]['Plan']

            t, q, f = _parse_query_plan(plan)
            table_names.extend(t)
            queries.extend(q)

            function_names = list(set(function_names) | set(f))

        except ValueError:
            log.error('Could not parse query plan')
            raise

    return table_names, function_names


def _parse_query_plan(
        plan: dict[str, Any]) -> tuple[list[str], list[str], list[str]]:
    '''
    Given a Postgres Query Plan object (parsed from the output of an EXPLAIN
    query), returns a tuple with three items:

    * A list of tables involved
    * A list of remaining queries to parse
    * A list of function names involved
    '''

    table_names: list[str] = []
    queries: list[str] = []
    functions: list[str] = []

    if plan.get('Relation Name'):
        table_names.append(plan['Relation Name'])
    if 'Function Name' in plan:
        if plan['Function Name'].startswith(
                'crosstab'):
            try:
                queries.append(_get_subquery_from_crosstab_call(
                    plan['Function Call']))
            except ValueError:
                table_names.append('_unknown_crosstab_sql')
        else:
            functions.append(plan['Function Name'])

    if 'Plans' in plan:
        for child_plan in plan['Plans']:
            t, q, f = _parse_query_plan(child_plan)
            table_names.extend(t)
            queries.extend(q)
            functions.extend(f)

    return table_names, queries, functions


def _get_function_names_from_sql(sql: str):
    function_names: list[str] = []

    def _get_function_names(tokens: Iterable[Any]):
        for token in tokens:
            if isinstance(token, sqlparse.sql.Function):
                function_name = cast(str, token.get_name())
                if function_name not in function_names:
                    function_names.append(function_name)
            if hasattr(token, 'tokens'):
                _get_function_names(token.tokens)

    parsed = sqlparse.parse(sql)[0]
    _get_function_names(parsed.tokens)

    return function_names


def _get_subquery_from_crosstab_call(ct: str):
    """
    Crosstabs are a useful feature some sites choose to enable on
    their datastore databases. To support the sql parameter passed
    safely we accept only the simple crosstab(text) form where text
    is a literal SQL string, otherwise raise ValueError
    """
    if not ct.startswith("crosstab('") or not ct.endswith("'::text)"):
        raise ValueError('only simple crosstab calls supported')
    ct = ct[10:-8]
    if "'" in ct.replace("''", ""):
        raise ValueError('only escaped single quotes allowed in query')
    return ct.replace("''", "'")


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
    Extensions should not show action buttons (i.e.) next to the Manage / Data API core ones
    """

    return "midnight-blue" not in tk.config.get("ckan.base_templates_folder")
