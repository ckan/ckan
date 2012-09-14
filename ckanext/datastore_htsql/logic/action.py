import logging
import pylons
from htsql import HTSQL
from htsql.core.cmd.command import UniversalCmd
from htsql.core.cmd.act import analyze
import ckan.plugins as p
import ckan.logic as logic
from ckanext.datastore import db

log = logging.getLogger(__name__)
_get_or_bust = logic.get_or_bust


@logic.side_effect_free
def datastore_search_htsql(context, data_dict):
    '''Execute HTSQL-Queries on the datastore.

    :param htsql: htsql statement
    :type htsql: string

    :returns: a dictionary containing the search results.
              keys: fields: columns for results
                    records: results from the query
    :rtype: dictionary

    '''
    query = _get_or_bust(data_dict, 'htsql')
    query = str(query)
    print query

    uri = pylons.config['ckan.datastore_read_url']
    engine = db._get_engine(None, {'connection_url': uri})

    htsql = HTSQL(None, {'tweak.sqlalchemy': {'engine': engine}, 'tweak.timeout': {'timeout': 1000}})

    with htsql:
        cmd = UniversalCmd(query)
        plan = analyze(cmd)
        sql = plan.statement.sql

    data_dict['sql'] = sql

    action = p.toolkit.get_action('datastore_search_sql')
    result = action(context, data_dict)
    result['htsql'] = query
    return result
