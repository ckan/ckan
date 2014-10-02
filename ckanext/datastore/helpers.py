import logging
import json


log = logging.getLogger(__name__)


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
