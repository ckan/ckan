import logging
import json

import sqlparse

import paste.deploy.converters as converters


log = logging.getLogger(__name__)


def get_list(input, strip_values=True):
    '''Transforms a string or list to a list'''
    if input is None:
        return
    if input == '':
        return []

    l = converters.aslist(input, ',', True)
    if strip_values:
        return [_strip(x) for x in l]
    else:
        return l


def is_single_statement(sql):
    '''Returns True if received SQL string contains at most one statement'''
    return len(sqlparse.split(sql)) <= 1


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


def get_table_names_from_sql(context, sql):
    '''Parses the output of EXPLAIN (FORMAT JSON) looking for table names

    It performs an EXPLAIN query against the provided SQL, and parses
    the output recusively looking for "Relation Name".

    Note that this requires Postgres 9.x.

    :param context: a CKAN context dict. It must contain a 'connection' key
        with the current DB connection.
    :type context: dict
    :param sql: the SQL statement to parse for table names
    :type sql: string

    :rtype: list of strings
    '''

    def _get_table_names_from_plan(plan):

        table_names = []

        if plan.get('Relation Name'):
            table_names.append(plan['Relation Name'])

        if 'Plans' in plan:
            for child_plan in plan['Plans']:
                table_name = _get_table_names_from_plan(child_plan)
                if table_name:
                    table_names.extend(table_name)

        return table_names

    result = context['connection'].execute(
        'EXPLAIN (FORMAT JSON) {0}'.format(sql)).fetchone()

    table_names = []

    try:
        query_plan = json.loads(result['QUERY PLAN'])
        plan = query_plan[0]['Plan']

        table_names.extend(_get_table_names_from_plan(plan))

    except ValueError:
        log.error('Could not parse query plan')

    return table_names


def literal_string(s):
    """
    Return s as a postgres literal string
    """
    return u"'" + s.replace(u"'", u"''").replace(u'\0', '') + u"'"


def identifier(s):
    """
    Return s as a quoted postgres identifier
    """
    return u'"' + s.replace(u'"', u'""').replace(u'\0', '') + u'"'
