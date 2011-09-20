from sqlalchemy import or_
import json
from pylons import config
from paste.util.multidict import MultiDict 
from paste.deploy.converters import asbool
from ckan import model
from common import make_connection, SearchError
import logging
log = logging.getLogger(__name__)

_open_licenses = None

VALID_SOLR_PARAMETERS = set([
    'q', 'fl', 'fq', 'rows', 'sort', 'start', 'wt', 'qf',
    'filter_by_downloadable', 'filter_by_openness',
    'facet', 'facet.mincount', 'facet.limit', 'facet.field'
])

# for (solr) package searches, this specifies the fields that are searched 
# and their relative weighting
QUERY_FIELDS = "name^4 title^4 tags^2 groups^2 text"

class QueryOptions(dict):
    """
    Options specify aspects of the search query which are only tangentially related 
    to the query terms (such as limits, etc.).
    """
    
    BOOLEAN_OPTIONS = ['filter_by_downloadable', 'filter_by_openness', 'all_fields']
    INTEGER_OPTIONS = ['offset', 'limit']

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
                    raise SearchError('Value for search option %r must be True or False (1 or 0) but received %r' % (key, value))
            elif key in self.INTEGER_OPTIONS:
                try:
                    value = int(value)
                except ValueError:
                    raise SearchError('Value for search option %r must be an integer but received %r' % (key, value))
            self[key] = value    
    
    def __getattr__(self, name):
        return self.get(name)
        
    def __setattr__(self, name, value):
        self[name] = value


class QueryParser(object):
    """
    The query parser will take any incoming query specifications and turn 
    them into field-specific and general query parts. 
    """
    
    def __init__(self, query, terms, fields):
        self._query = query
        self._terms = terms
        self._fields = MultiDict(fields)
    
    @property    
    def query(self):
        if not hasattr(self, '_combined_query'):
            parts = [self._query if self._query is not None else '']
            
            for term in self._terms:
                if term.find(u' ') != -1:
                    term = u"\"%s\"" % term
                parts.append(term.strip())
                
            for field, value in self._fields.items():
                if field != 'tags' and value.find(' ') != -1:
                    value = u"\"%s\"" % value
                parts.append(u"%s:%s" % (field.strip(), value.strip()))
                
            self._combined_query = u' '.join(parts)
        return self._combined_query
    
    def _query_tokens(self):
        """ Split the query string, leaving quoted strings intact. """
        if self._query:
            inside_quote = False
            buf = u''
            for ch in self._query:
                if ch == u' ' and not inside_quote:
                    if len(buf):
                        yield buf.strip()
                    buf = u''
                elif ch == inside_quote:
                    inside_quote = False
                elif ch in [u"\"", u"'"]:
                    inside_quote = ch
                else:
                    buf += ch
            if len(buf):
                yield buf.strip()
    
    def _parse_query(self):
        """ Decompose the query string into fields and terms. """
        self._combined_fields = MultiDict(self._fields)
        self._combined_terms = list(self._terms)
        for token in self._query_tokens():
            colon_pos = token.find(u':')
            if colon_pos != -1:
                field = token[:colon_pos]
                value = token[colon_pos+1:]
                value = value.strip('"').strip("'").strip()
                self._combined_fields.add(field, value)
            else:
                self._combined_terms.append(token)
    
    @property
    def fields(self):
        if not hasattr(self, '_combined_fields'):
            self._parse_query()
        return self._combined_fields
    
    @property
    def terms(self):
        if not hasattr(self, '_combined_terms'):
            self._parse_query()
        return self._combined_terms
    
    def validate(self):
        """ Check that this is a valid query. """
        pass
    
    def __str__(self):
        return self.query
        
    def __repr__(self):
        return "Query(%r)" % self.query


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
    
    def _format_results(self):
        if not self.options.return_objects and len(self.results):
            if self.options.all_fields:
                self.results = [r.as_dict() for r in self.results]
            else:
                attr_name = self.options.ref_entity_with_attr
                self.results = [getattr(entity, attr_name) for entity in self.results]

    def get_all_entity_ids(self, max_results=1000):
        """
        Return a list of the IDs of all indexed packages.
        """
        return []
    
    def run(self, query=None, terms=[], fields={}, facet_by=[], options=None, **kwargs):
        if options is None:
            options = QueryOptions(**kwargs) 
        else:
            options.update(kwargs)
        self.options = options
        self.options.validate()
        self.facet_by = facet_by
        self.facets = dict()
        self.query = QueryParser(query, terms, fields)
        self.query.validate()
        self._run()
        self._format_results()
        return {'results': self.results, 'count': self.count}
        
    def _run(self):
        raise SearchError("SearchQuery._run() not implemented!")

    def _db_query(self, q):
        # Run the query
        self.count = q.count()
        q = q.offset(self.options.get('offset'))
        q = q.limit(self.options.get('limit'))
        
        self.results = []
        for result in q:
            if isinstance(result, tuple) and isinstance(result[0], model.DomainObject):
                # This is the case for order_by rank due to the add_column.
                self.results.append(result[0])
            else:
                self.results.append(result)
        
    # convenience, allows to query(..)
    __call__ = run


class TagSearchQuery(SearchQuery):
    """Search for tags in plain SQL."""
    def _run(self):
        q = model.Session.query(model.Tag)
        q = q.distinct().join(model.Tag.package_tags)
        terms = list(self.query.terms)
        for field, value in self.query.fields.items():
            if field in ('tag', 'tags'):
                terms.append(value)
        if not len(terms):
            return
        for term in terms:
            q = q.filter(model.Tag.name.contains(term.lower()))
        self._db_query(q)


class ResourceSearchQuery(SearchQuery):
    """ Search for resources in plain SQL. """
    def _run(self):
        q = model.Session.query(model.Resource) # TODO authz
        if self.query.terms:
            raise SearchError('Only field specific terms allowed in resource search.')
        self.options.ref_entity_with_attr = 'id' # has no name
        resource_fields = model.Resource.get_columns()
        for field, terms in self.query.fields.items():
            if isinstance(terms, basestring):
                terms = terms.split()
            if field not in resource_fields:
                raise SearchError('Field "%s" not recognised in Resource search.' % field)
            for term in terms:
                model_attr = getattr(model.Resource, field)
                if field == 'hash':                
                    q = q.filter(model_attr.ilike(unicode(term) + '%'))
                elif field in model.Resource.get_extra_columns():
                    model_attr = getattr(model.Resource, 'extras')

                    like = or_(
                        model_attr.ilike(u'''%%"%s": "%%%s%%",%%''' % (field, term)),
                        model_attr.ilike(u'''%%"%s": "%%%s%%"}''' % (field, term))
                    )
                    q = q.filter(like)
                else:
                    q = q.filter(model_attr.ilike('%' + unicode(term) + '%'))
        
        order_by = self.options.order_by
        if order_by is not None:
            if hasattr(model.Resource, order_by):
                q = q.order_by(getattr(model.Resource, order_by))
        self._db_query(q)


class PackageSearchQuery(SearchQuery):
    def get_all_entity_ids(self, max_results=1000):
        """
        Return a list of the IDs of all indexed packages.
        """
        query = "*:*"
        fq = "+site_id:\"%s\" " % config.get('ckan.site_id')
        fq += "+state:active "

        conn = make_connection()
        try:
            data = conn.query(query, fq=fq, rows=max_results, fields='id')
        finally:
            conn.close()

        return [r.get('id') for r in data.results]

    def run(self, query):
        # check that query keys are valid
        if not set(query.keys()) <= VALID_SOLR_PARAMETERS:
            invalid_params = [s for s in set(query.keys()) - VALID_SOLR_PARAMETERS]
            raise SearchError("Invalid search parameters: %s" % invalid_params)

        # default query is to return all documents
        q = query.get('q')
        if not q or q == '""' or q == "''":
            query['q'] = "*:*"

        # number of results
        query['rows'] = min(1000, int(query.get('rows', 10)))

        # order by score if no 'sort' term given
        order_by = query.get('sort')
        if order_by == 'rank' or order_by is None: 
            query['sort'] = 'score desc, name asc'

        # show only results from this CKAN instance
        fq = query.get('fq', '')
        if not '+site_id:' in fq:
            fq += ' +site_id:"%s"' % config.get('ckan.site_id')

        # filter for package status       
        if not '+state:' in fq:
            fq += " +state:active"
        query['fq'] = fq

        # faceting
        query['facet'] = query.get('facet', 'true')
        query['facet.limit'] = query.get('facet.limit', config.get('search.facets.limit', '50'))
        query['facet.mincount'] = query.get('facet.mincount', 1)

        # return the package ID and search scores
        query['fl'] = query.get('fl', 'name')
        
        # return results as json encoded string
        query['wt'] = query.get('wt', 'json')

        # check if filtering by downloadable or open license
        if int(query.get('filter_by_downloadable', 0)):
            query['fq'] += u" +res_url:[* TO *] " # not null resource URL 
        if int(query.get('filter_by_openness', 0)):
            licenses = ["license_id:%s" % id for id in self.open_licenses]
            licenses = " OR ".join(licenses)
            query['fq'] += " +(%s) " % licenses

        # query field weighting
        query['defType'] = 'edismax'
        query['tie'] = '0.5'
        query['qf'] = query.get('qf', QUERY_FIELDS)

        conn = make_connection()
        try:
            data = json.loads(conn.raw_query(**query))
            response = data['response']
            self.count = response.get('numFound', 0)
            self.results = response.get('docs', [])

            # if just fetching the id or name, return a list instead of a dict
            if query.get('fl') in ['id', 'name']:
                self.results = [r.get(query.get('fl')) for r in self.results]

            # get facets and convert facets list to a dict
            self.facets = data.get('facet_counts', {}).get('facet_fields', {})
            for field, values in self.facets.iteritems():
                self.facets[field] = dict(zip(values[0::2], values[1::2]))
        except Exception, e:
            log.exception(e)
            raise SearchError(e)
        finally:
            conn.close()
        
        return {'results': self.results, 'count': self.count}
