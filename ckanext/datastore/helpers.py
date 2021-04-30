# encoding: utf-8

import json
import logging

import paste.deploy.converters as converters
import sqlparse

from ckan.plugins.toolkit import get_action, ObjectNotFound, NotAuthorized

log = logging.getLogger(__name__)


def is_single_statement(sql):
    '''Returns True if received SQL string contains at most one statement'''
    return len(sqlparse.split(sql)) <= 1


def is_valid_field_name(name):
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


def is_valid_table_name(name):
    if '%' in name:
        return False
    return is_valid_field_name(name)


def get_list(input, strip_values=True):
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


def validate_int(i, non_negative=False):
    try:
        i = int(i)
    except ValueError:
        return False
    return i >= 0 or not non_negative


def _strip(input):
    if isinstance(input, basestring) and len(input) and input[0] == input[-1]:
        return input.strip().strip('"')
    return input


def should_fts_index_field_type(field_type):
    return field_type.lower() in ['tsvector', 'text', 'number']


def get_table_and_function_names_from_sql(context, sql):
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

    table_names = []
    function_names = []

    def _parse_query_plan(plan):

        table_names = []
        function_names = []

        if plan.get('Relation Name'):
            table_names.append(plan['Relation Name'])
        if 'Function Name' in plan:
            function_names.append(plan['Function Name'])

        if 'Plans' in plan:
            for child_plan in plan['Plans']:
                t, f = _parse_query_plan(child_plan)
                table_names.extend(t)
                function_names.extend(f)

        return table_names, function_names

    function_names.extend(_get_function_names_from_sql(sql))

    result = context['connection'].execute(
        'EXPLAIN (FORMAT JSON) {0}'.format(sql.encode('utf-8'))).fetchone()

    try:
        if isinstance(result['QUERY PLAN'], basestring):
            query_plan = json.loads(result['QUERY PLAN'])
        else:
            query_plan = result['QUERY PLAN']
        plan = query_plan[0]['Plan']

        t, f = _parse_query_plan(plan)

        table_names.extend(t)
        function_names = list(set(function_names) | set(f))

    except ValueError:
        log.error('Could not parse query plan')

    return table_names, function_names


def _get_function_names_from_sql(sql):
    function_names = []

    def _get_function_names(tokens):
        for token in tokens:
            if isinstance(token, sqlparse.sql.Function):
                function_name = token.get_name()
                if function_name not in function_names:
                    function_names.append(function_name)
            if hasattr(token, 'tokens'):
                _get_function_names(token.tokens)

    parsed = sqlparse.parse(sql)[0]
    _get_function_names(parsed.tokens)

    return function_names


def datastore_dictionary(resource_id):
    """
    Return the data dictionary info for a resource
    """
    try:
        return [
            f for f in get_action('datastore_search')(
                None, {
                    u'resource_id': resource_id,
                    u'limit': 0,
                    u'include_total': False})['fields']
            if not f['id'].startswith(u'_')]
    except (ObjectNotFound, NotAuthorized):
        return []
