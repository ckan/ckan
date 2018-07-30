# encoding: utf-8

import re
import logging

from ckan.common import config
import pysolr
from paste.deploy.converters import asbool
from paste.util.multidict import MultiDict
import six

from ckan.lib.search.common import make_connection, SearchError, SearchQueryError
import ckan.logic as logic
import ckan.model as model

log = logging.getLogger(__name__)

_open_licenses = None

VALID_SOLR_PARAMETERS = set([
    'q', 'fl', 'fq', 'rows', 'sort', 'start', 'wt', 'qf', 'bf', 'boost',
    'facet', 'facet.mincount', 'facet.limit', 'facet.field',
    'extras', 'fq_list', 'tie', 'defType', 'mm'
])

# for (solr) package searches, this specifies the fields that are searched
# and their relative weighting
QUERY_FIELDS = "name^4 title^4 tags^2 groups^2 text"

solr_regex = re.compile(r'([\\+\-&|!(){}\[\]^"~*?:])')

def escape_legacy_argument(val):
    # escape special chars \+-&|!(){}[]^"~*?:
    return solr_regex.sub(r'\\\1', val)

def convert_legacy_parameters_to_solr(legacy_params):
    '''API v1 and v2 allowed search params that the SOLR syntax does not
    support, so use this function to convert those to SOLR syntax.
    See tests for examples.

    raises SearchQueryError on invalid params.
    '''
    options = QueryOptions(**legacy_params)
    options.validate()
    solr_params = legacy_params.copy()
    solr_q_list = []
    if solr_params.get('q'):
        solr_q_list.append(solr_params['q'].replace('+', ' '))
    non_solr_params = set(legacy_params.keys()) - VALID_SOLR_PARAMETERS
    for search_key in non_solr_params:
        value_obj = legacy_params[search_key]
        value = value_obj.replace('+', ' ') if isinstance(value_obj, six.string_types) else value_obj
        if search_key == 'all_fields':
            if value:
                solr_params['fl'] = '*'
        elif search_key == 'offset':
            solr_params['start'] = value
        elif search_key == 'limit':
            solr_params['rows'] = value
        elif search_key == 'order_by':
            solr_params['sort'] = '%s asc' % value
        elif search_key == 'tags':
            if isinstance(value_obj, list):
                tag_list = value_obj
            elif isinstance(value_obj, six.string_types):
                tag_list = [value_obj]
            else:
                raise SearchQueryError('Was expecting either a string or JSON list for the tags parameter: %r' % value)
            solr_q_list.extend(['tags:"%s"' % escape_legacy_argument(tag) for tag in tag_list])
        else:
            if len(value.strip()):
                value = escape_legacy_argument(value)
                if ' ' in value:
                    value = '"%s"' % value
                solr_q_list.append('%s:%s' % (search_key, value))
        del solr_params[search_key]
    solr_params['q'] = ' '.join(solr_q_list)
    if non_solr_params:
        log.debug('Converted legacy search params from %r to %r',
                 legacy_params, solr_params)
    return solr_params


class QueryOptions(dict):
    """
    Options specify aspects of the search query which are only tangentially related
    to the query terms (such as limits, etc.).
    NB This is used only by legacy package search and current resource & tag search.
       Modern SOLR package search leaves this to SOLR syntax.
    """

    BOOLEAN_OPTIONS = ['all_fields']
    INTEGER_OPTIONS = ['offset', 'limit']
    UNSUPPORTED_OPTIONS = ['filter_by_downloadable', 'filter_by_openness']

    def __init__(self, **kwargs):
        from ckan.lib.search import DEFAULT_OPTIONS

        # set values according to the defaults
        for option_name, default_value in DEFAULT_OPTIONS.items():
            if not option_name in self:
                self[option_name] = default_value

        super(QueryOptions, self).__init__(**kwargs)

    def validate(self):
        for key, value in self.items():
            if key in self.BOOLEAN_OPTIONS:
                try:
                    value = asbool(value)
                except ValueError:
                    raise SearchQueryError('Value for search option %r must be True or False (1 or 0) but received %r' % (key, value))
            elif key in self.INTEGER_OPTIONS:
                try:
                    value = int(value)
                except ValueError:
                    raise SearchQueryError('Value for search option %r must be an integer but received %r' % (key, value))
            elif key in self.UNSUPPORTED_OPTIONS:
                    raise SearchQueryError('Search option %r is not supported' % key)
            self[key] = value

    def __getattr__(self, name):
        return self.get(name)

    def __setattr__(self, name, value):
        self[name] = value


class SearchQuery(object):
    """
    A query is ... when you ask the search engine things. SearchQuery is intended
    to be used for only one query, i.e. it sets state. Definitely not thread-safe.
    """

    def __init__(self):
        self.results = []
        self.count = 0

    @property
    def open_licenses(self):
        # this isn't exactly the very best place to put these, but they stay
        # there persistently.
        # TODO: figure out if they change during run-time.
        global _open_licenses
        if not isinstance(_open_licenses, list):
            _open_licenses = []
            for license in model.Package.get_license_register().values():
                if license and license.isopen():
                    _open_licenses.append(license.id)
        return _open_licenses

    def get_all_entity_ids(self, max_results=1000):
        """
        Return a list of the IDs of all indexed packages.
        """
        return []

    def run(self, query=None, terms=[], fields={}, facet_by=[], options=None, **kwargs):
        raise SearchError("SearchQuery.run() not implemented!")

    # convenience, allows to query(..)
    __call__ = run


class TagSearchQuery(SearchQuery):
    """Search for tags."""
    def run(self, query=None, fields=None, options=None, **kwargs):
        query = [] if query is None else query
        fields = {} if fields is None else fields

        if options is None:
            options = QueryOptions(**kwargs)
        else:
            options.update(kwargs)

        if isinstance(query, six.string_types):
            query = [query]

        query = query[:] # don't alter caller's query list.
        for field, value in fields.items():
            if field in ('tag', 'tags'):
                query.append(value)

        context = {'model': model, 'session': model.Session}
        data_dict = {
            'query': query,
            'offset': options.get('offset'),
            'limit': options.get('limit')
        }
        results = logic.get_action('tag_search')(context, data_dict)

        if not options.return_objects:
            # if options.all_fields is set, return a dict
            # if not, return a list of resource IDs
            if options.all_fields:
                results['results'] = [r.as_dict() for r in results['results']]
            else:
                results['results'] = [r['name'] for r in results['results']]

        self.count = results['count']
        self.results = results['results']
        return results


class ResourceSearchQuery(SearchQuery):
    """Search for resources."""
    def run(self, fields={}, options=None, **kwargs):
        if options is None:
            options = QueryOptions(**kwargs)
        else:
            options.update(kwargs)

        context = {
            'model':model,
            'session': model.Session,
            'search_query': True,
        }

        # Transform fields into structure required by the resource_search
        # action.
        query = []
        for field, terms in fields.items():
            if isinstance(terms, six.string_types):
                terms = terms.split()
            for term in terms:
                query.append(':'.join([field, term]))

        data_dict = {
            'query': query,
            'offset': options.get('offset'),
            'limit': options.get('limit'),
            'order_by': options.get('order_by')
        }
        results = logic.get_action('resource_search')(context, data_dict)

        if not options.return_objects:
            # if options.all_fields is set, return a dict
            # if not, return a list of resource IDs
            if options.all_fields:
                results['results'] = [r.as_dict() for r in results['results']]
            else:
                results['results'] = [r.id for r in results['results']]

        self.count = results['count']
        self.results = results['results']
        return results


class PackageSearchQuery(SearchQuery):
    def get_all_entity_ids(self, max_results=1000):
        """
        Return a list of the IDs of all indexed packages.
        """
        query = "*:*"
        fq = "+site_id:\"%s\" " % config.get('ckan.site_id')
        fq += "+state:active "

        conn = make_connection()
        data = conn.search(query, fq=fq, rows=max_results, fields='id')
        return [r.get('id') for r in data.docs]

    def get_index(self,reference):
        query = {
            'rows': 1,
            'q': 'name:"%s" OR id:"%s"' % (reference,reference),
            'wt': 'json',
            'fq': 'site_id:"%s"' % config.get('ckan.site_id')}

        try:
            if query['q'].startswith('{!'):
                raise SearchError('Local parameters are not supported.')
        except KeyError:
            pass

        conn = make_connection(decode_dates=False)
        log.debug('Package query: %r' % query)
        try:
            solr_response = conn.search(**query)
        except pysolr.SolrError as e:
            raise SearchError('SOLR returned an error running query: %r Error: %r' %
                              (query, e))

        if solr_response.hits == 0:
            raise SearchError('Dataset not found in the search index: %s' % reference)
        else:
            return solr_response.docs[0]


    def run(self, query, permission_labels=None, **kwargs):
        '''
        Performs a dataset search using the given query.

        :param query: dictionary with keys like: q, fq, sort, rows, facet
        :type query: dict
        :param permission_labels: filter results to those that include at
            least one of these labels. None to not filter (return everything)
        :type permission_labels: list of unicode strings; or None

        :returns: dictionary with keys results and count

        May raise SearchQueryError or SearchError.
        '''
        assert isinstance(query, (dict, MultiDict))
        # check that query keys are valid
        if not set(query.keys()) <= VALID_SOLR_PARAMETERS:
            invalid_params = [s for s in set(query.keys()) - VALID_SOLR_PARAMETERS]
            raise SearchQueryError("Invalid search parameters: %s" % invalid_params)

        # default query is to return all documents
        q = query.get('q')
        if not q or q == '""' or q == "''":
            query['q'] = "*:*"

        # number of results
        rows_to_return = min(1000, int(query.get('rows', 10)))
        if rows_to_return > 0:
            # #1683 Work around problem of last result being out of order
            #       in SOLR 1.4
            rows_to_query = rows_to_return + 1
        else:
            rows_to_query = rows_to_return
        query['rows'] = rows_to_query

        fq = []
        if 'fq' in query:
            fq.append(query['fq'])
        fq.extend(query.get('fq_list', []))

        # show only results from this CKAN instance
        fq.append('+site_id:%s' % solr_literal(config.get('ckan.site_id')))

        # filter for package status
        if not '+state:' in query.get('fq', ''):
            fq.append('+state:active')

        # only return things we should be able to see
        if permission_labels is not None:
            fq.append('+permission_labels:(%s)' % ' OR '.join(
                solr_literal(p) for p in permission_labels))
        query['fq'] = fq

        # faceting
        query['facet'] = query.get('facet', 'true')
        query['facet.limit'] = query.get('facet.limit', config.get('search.facets.limit', '50'))
        query['facet.mincount'] = query.get('facet.mincount', 1)

        # return the package ID and search scores
        query['fl'] = query.get('fl', 'name')

        # return results as json encoded string
        query['wt'] = query.get('wt', 'json')

        # If the query has a colon in it then consider it a fielded search and do use dismax.
        defType = query.get('defType', 'dismax')
        if ':' not in query['q'] or defType == 'edismax':
            query['defType'] = defType
            query['tie'] = query.get('tie', '0.1')
            # this minimum match is explained
            # http://wiki.apache.org/solr/DisMaxQParserPlugin#mm_.28Minimum_.27Should.27_Match.29
            query['mm'] = query.get('mm', '2<-1 5<80%')
            query['qf'] = query.get('qf', QUERY_FIELDS)

        try:
            if query['q'].startswith('{!'):
                raise SearchError('Local parameters are not supported.')
        except KeyError:
            pass

        conn = make_connection(decode_dates=False)
        log.debug('Package query: %r' % query)
        try:
            solr_response = conn.search(**query)
        except pysolr.SolrError as e:
            # Error with the sort parameter.  You see slightly different
            # error messages depending on whether the SOLR JSON comes back
            # or Jetty gets in the way converting it to HTML - not sure why
            #
            if e.args and isinstance(e.args[0], str):
                if "Can't determine a Sort Order" in e.args[0] or \
                        "Can't determine Sort Order" in e.args[0] or \
                        'Unknown sort order' in e.args[0]:
                    raise SearchQueryError('Invalid "sort" parameter')
            raise SearchError('SOLR returned an error running query: %r Error: %r' %
                              (query, e))
        self.count = solr_response.hits
        self.results = solr_response.docs


        # #1683 Filter out the last row that is sometimes out of order
        self.results = self.results[:rows_to_return]

        # get any extras and add to 'extras' dict
        for result in self.results:
            extra_keys = filter(lambda x: x.startswith('extras_'), result.keys())
            extras = {}
            for extra_key in extra_keys:
                value = result.pop(extra_key)
                extras[extra_key[len('extras_'):]] = value
            if extra_keys:
                result['extras'] = extras

        # if just fetching the id or name, return a list instead of a dict
        if query.get('fl') in ['id', 'name']:
            self.results = [r.get(query.get('fl')) for r in self.results]

        # get facets and convert facets list to a dict
        self.facets = solr_response.facets.get('facet_fields', {})
        for field, values in six.iteritems(self.facets):
            self.facets[field] = dict(zip(values[0::2], values[1::2]))

        return {'results': self.results, 'count': self.count}


def solr_literal(t):
    '''
    return a safe literal string for a solr query. Instead of escaping
    each of + - && || ! ( ) { } [ ] ^ " ~ * ? : \ / we're just dropping
    double quotes -- this method currently only used by tokens like site_id
    and permission labels.
    '''
    return u'"' + t.replace(u'"', u'') + u'"'
