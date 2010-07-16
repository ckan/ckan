import logging

from paste.util.multidict import MultiDict 
from ckan import model

log = logging.getLogger(__name__)

class SearchError(Exception): pass

class SearchBackend(object):
    """
    A search backend describes the engine used to actually maintain data. This can be 
    something like Solr, Xapian, or just a mapping onto SQL queries. 
    
    The backend stores a mapping of ``SearchIndex``, ``SearchQuery`` pairs for all 
    entity types that are supposed to be queried using this engine. 
    
    Entity types can be given as classes, objects or strings that uniquely identify a 
    ``DomainObject`` type used in CKAN.
    """
    
    def __init__(self):
        self._typed_queries = {}
        self._typed_indices = {}
        self._setup()
        
    def _setup(self):
        """ This method is overridden by subclasses to actually register handlers """
        pass
    
    def _normalize_type(self, _type):
        if isinstance(_type, model.DomainObject):
            _type = _type.__class__
        if isinstance(_type, type):
            _type = _type.__name__
        return _type.strip().lower()
    
    def register(self, _type, index_class, query_class):
        """ Register a type by setting both query and index classes. """
        _type = self._normalize_type(_type)
        self._typed_queries[_type] = query_class
        self._typed_indices[_type] = index_class
        
    def unregister(self, _type):
        """ TODO: Find out what would possibly use this. """
        _type = self._normalize_type(_type)
        if _type in self._typed_queries:
            del self._typed_queries[_type]
        if _type in self._typed_indices:
            del self._typed_indices[_type]
    
    def query_for(self, _type):
        """ Get a SearchQuery instance sub-class suitable for the specified type. """
        try:
            _type_n = self._normalize_type(_type)
            return self._typed_queries[_type_n](self)
        except KeyError, ke:
            raise SearchError("Unknown search type: %s" % _type)
            
    def index_for(self, _type):
        """ Get a SearchIndex instance sub-class suitable for the specified type. """
        try:
            _type_n = self._normalize_type(_type)
            return self._typed_indices[_type_n](self)
        except KeyError, ke:
            raise SearchError("Unknown search type: %s" % _type)
            
    def types(self):
        return self._typed_queries.keys()
            

class SearchQuery(object):
    """
    A query is ... when you ask the search engine things. SearchQuery is intended 
    to be used for only one query, i.e. it sets state. Definitely not thread-safe.
    """
    
    def __init__(self, backend):
        self.backend = backend
        self.results = []
        self.count = 0
    
    @property
    def open_licenses(self):
        # backend isn't exactly the very best place to put these, but they stay
        # there persistently. 
        # TODO: figure out if they change during run-time. 
        if not hasattr(self.backend, '_open_licenses'):
            self.backend._open_licenses = []
            for license in model.Package.get_license_register().values():
                if license and license.isopen():
                    self.backend._open_licenses.append(license.id)
        return self.backend._open_licenses
    
    def _format_results(self):
        if not self.options.return_objects and len(self.results):
            if self.options.all_fields:
                self.results = [r.as_dict() for r in self.results]
            elif not isinstance(self.results[0], basestring):
                attr_name = self.options.ref_entity_with_attr
                self.results = [getattr(entity, attr_name) for entity in self.results]
    
    def run(self, query=None, terms=[], fields={}, options=None, **kwargs):
        if options is None:
            options = QueryOptions(**kwargs) 
        else:
            options.update(kwargs)
        self.options = options
        self.query = QueryParser(query, terms, fields)
        self.query.validate()
        self._run()
        self._format_results()
        return {'results': self.results, 'count': self.count}
        
    def _run(self):
        raise SearchError("SearchQuery._run() not implemented!")


class QueryOptions(dict):
    """
    Options specify aspects of the search query which are only tangentially related 
    to the query terms (such as limits, etc.).
    """
    
    BOOLEAN_OPTIONS = ['filter_by_downloadable', 'filter_by_openness', 'all_fields']
    INTEGER_OPTIONS = ['offset', 'limit']

    def __init__(self, **kwargs):
        super(QueryOptions, self).__init__(**kwargs)
        from ckan.lib.search import DEFAULT_OPTIONS
        
        # set values according to the defaults
        for option_name, default_value in DEFAULT_OPTIONS.items():
            if not option_name in self:
                self[option_name] = default_value
        
        for boolean_option in self.BOOLEAN_OPTIONS:
            self[boolean_option] = self[boolean_option] == 1 or self[boolean_option]
            
        for integer_option in self.INTEGER_OPTIONS:
            self[integer_option] = int(self[integer_option])
            
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
                if value.find(' ') != -1:
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
                if len(value):
                    self._combined_fields[field] = value
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
        if not len(self.query):
            raise SearchError("No query has been specified")
    
    def __str__(self):
        return self.query
        
    def __repr__(self):
        return "Query(%s)" % self


class SearchIndex(object):
    """ 
    A search index handles the management of documents of a specific type in the 
    index, but no queries. 
    The default implementation maps many of the methods, so most subclasses will 
    only have to implement ``update_dict`` and ``remove_dict``. 
    """    
    
    def __init__(self, backend):
        self.backend = backend
    
    def insert_dict(self, data):
        """ Insert new data from a dictionary. """
        return self.update_dict(data)
        
    def insert_entity(self, entity):
        """ Insert new data from a domain object. """
        return self.insert_dict(entity.as_dict())
    
    def update_dict(self, data):
        """ Update data from a dictionary. """
        log.warn("NOOP Index: %s" % ",".join(data.keys()))
    
    def update_entity(self, entity):
        """ Update data from a domain object. """
        # in convention we trust:
        return self.update_dict(entity.as_dict())
    
    def remove_dict(self, data):
        """ Delete an index entry uniquely identified by ``data``. """
        log.warn("NOOP Delete: %s" % ",".join(data.keys()))
        
    def remove_entity(self, entity):
        """ Delete ``entity``. """
        return self.remove_dict(entity.as_dict())
        
    def clear(self):
        """ Delete the complete index. """
        log.warn("NOOP Index reset")
        
class NoopSearchIndex(SearchIndex): pass
