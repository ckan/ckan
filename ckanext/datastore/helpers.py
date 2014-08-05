import logging
import json
import re

import sqlalchemy
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


def get_table_names_from_sql(context, sql):
    '''Parses the output of EXPLAIN (FORMAT JSON) looking for table names

    It performs an EXPLAIN query against the provided SQL, and parses
    the output recusively looking for "Relation Name".


    This requires Postgres 9.x. If an older version of Postgres is being run,
    it falls back to parse the text output of EXPLAIN. This is harder to parse
    and maintain, so it will be deprecated once support for Postgres < 9.x is
    dropped.


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

    try:
        result = context['connection'].execute(
            'EXPLAIN (FORMAT JSON) {0}'.format(sql)).fetchone()
    except sqlalchemy.exc.ProgrammingError, e:
        if 'syntax error at or near "format"' in str(e).lower():
            # Old version of Postgres, parse the text output instead
            return _get_table_names_from_sql_text(context, sql)
        raise

    table_names = []

    try:
        query_plan = json.loads(result['QUERY PLAN'])
        plan = query_plan[0]['Plan']

        table_names.extend(_get_table_names_from_plan(plan))

    except ValueError:
        log.error('Could not parse query plan')

    return table_names


def _get_table_names_from_sql_text(context, sql):
    '''Parses the output of EXPLAIN looking for table names

    It performs an EXPLAIN query against the provided SQL, and parses
    the output looking for "Scan on".

    Note that double quotes are removed from table names.

    This is to be used only on Postgres 8.x.

    This function should not be called directly, use
    `get_table_names_from_sql`.


    :param context: a CKAN context dict. It must contain a 'connection' key
        with the current DB connection.
    :type context: dict
    :param sql: the SQL statement to parse for table names
    :type sql: string

    :rtype: list of strings
    '''

    results = context['connection'].execute(
        'EXPLAIN {0}'.format(sql))

    pattern = re.compile('Scan on (.*)  ')

    table_names = []
    for result in results:
        query_plan = result['QUERY PLAN']

        match = pattern.search(query_plan)
        if match:
            table_names.append(match.group(1).strip('"'))

    return table_names
