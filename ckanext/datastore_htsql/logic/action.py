import logging
import ckan.plugins as p
import ckan.logic as logic

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
    htsql = _get_or_bust(data_dict, 'htsql')
    print htsql

    data_dict['sql'] = htsql

    action = p.toolkit.get_action('datastore_search_sql')
    return action(context, data_dict)
