import sqlalchemy
import simplejson

from pylons import config

import ckan.model as model

from ckan import authz

ENABLE_CACHING = bool(config.get('enable_caching', ''))
LIMIT_DEFAULT = 20

if ENABLE_CACHING:
    from pylons import cache
    our_cache = cache.get_cache('search_results', type='dbm')

class SearchOptions:
    # about the search
    q = None
    entity = 'package'
    limit = LIMIT_DEFAULT
    offset = 0
    filter_by_openness = False
    filter_by_downloadable = False

    # about presenting the results
    order_by = 'rank'
    all_fields = False
    return_objects = False

    def __init__(self, kw_dict):
        if not kw_dict.keys():
            raise Exception('no options supplied')

        for k,v in kw_dict.items():
            # Ensure boolean fields are boolean
            if k in ['filter_by_downloadable', 'filter_by_openness', 'all_fields']:
                v = v == 1 or v
            # Ensure integer fields are integer
            if k in ['offset', 'limit']:
                v = int(v)
            # Multiple tags params are added in list
            if hasattr(self, k) and k in ['tags', 'groups']:
                existing_val = getattr(self, k)
                if type(existing_val) == type([]):
                    v = existing_val + [v]
                else:
                    v = [existing_val, v]
            setattr(self, k, v)

    def __str__(self):
        return repr(self.__dict__)

class Search:
    _tokens = [ 'name', 'title', 'notes', 'tags', 'groups', 'author', 'maintainer', 'update_frequency', 'geographic_granularity', 'geographic_coverage', 'temporal_granularity', 'temporal_coverage', 'national_statistic', 'categories', 'precision', 'department', 'agency', 'external_reference']
    # Note: all tokens must be in the search vector (see model/full_search.py)
    _open_licenses = None

    def search(self, query_string):
        '''For the given basic query string, returns query results.'''
        options = SearchOptions({'q':query_string})
        return self.run(options)

    def query(self, options, username=None):
        '''For the given search options, returns a query object.'''
        self._options = options
        general_terms, field_specific_terms = self._parse_query_string()

        if not general_terms and \
           (self._options.entity != 'package' or not field_specific_terms):
            return None

        if self._options.entity == 'package':
            query = authz.Authorizer().authorized_query(username, model.Package)
            query = self._build_package_query(query, general_terms, field_specific_terms)
        elif self._options.entity == 'tag':
            query = self._build_tags_query(general_terms)
        elif self._options.entity == 'group':
            query = authz.Authorizer().authorized_query(username, model.Group)
            query = self._build_groups_query(query, general_terms)
        else:
            # error
            pass
        return query

    def run(self, options, username=None):
        '''For the given search options, returns query results.'''
        query = self.query(options, username)

        self._results = {}
        if not query:
            self._results['results'] = []
            self._results['count'] = 0
            return self._results

        self._run_query(query)
        self._format_results()
        return self._results

    def _parse_query_string(self):
        query_str = self._options.q
        
        # split query into terms
        # format: * double quotes enclose a single term. e.g. "War and Peace"
        #         * field:term or field:"longer term" means search only in that
        #           particular field for that term.
        terms = []
        if query_str:
            inside_quote = False
            buf = ''
            for ch in query_str:
                if ch == ' ' and not inside_quote:
                    if buf:
                        terms.append(buf.strip())
                    buf = ''
                elif ch == '"':
                    inside_quote = not inside_quote
                else:
                    buf += ch
            if buf:
                terms.append(buf)

        # split off field-specific terms
        field_specific_terms = {}
        general_terms = []
        for term in terms:
            
            # Look for 'token:'
            token = None
            colon_pos = term.find(':')
            if colon_pos != -1:
                token = term[:colon_pos]
                if token in self._tokens:
                    term = term[colon_pos+1:]
                    if term:
                        if not field_specific_terms.has_key(token):
                            field_specific_terms[token] = []
                        field_specific_terms[token].append(term)
                else:
                    general_terms.append(term)
            else:
                general_terms.append(term)

        # add field-specific terms that have come in via the options
        for token in self._tokens:
            if self._options.__dict__.has_key(token):
                field_specific_terms[token] = getattr(self._options, token)

        # special case - 'tags:' becomes a general term when searching
        # tag entities.
        if self._options.entity == 'tag' and field_specific_terms.has_key(u'tags'):
            general_terms.extend(field_specific_terms[u'tags'])
        
        
        return general_terms, field_specific_terms

    def _build_package_query(self, authorized_package_query,
                             general_terms, field_specific_terms):
        make_like = lambda x,y: x.ilike('%' + y + '%')
        query = authorized_package_query
        query = query.filter(model.package_search_table.c.package_id==model.Package.id)

        # Full search by general_terms (and field specific terms but not by field)
        terms_set = set()
        for term_list in field_specific_terms.values():
            if isinstance(term_list, (list, tuple)):
                for term in term_list:
                    terms_set.add(term)
            else:
                terms_set.add(term_list)
        for term in general_terms:
            terms_set.add(term)
        all_terms = ' '.join(terms_set)
        query = query.filter('package_search.search_vector '\
                                       '@@ plainto_tsquery(:terms)')
        query = query.params(terms=all_terms)
            
        # Filter by field_specific_terms
        for field, terms in field_specific_terms.items():
            if isinstance(terms, (str, unicode)):
                terms = terms.split()
            if field in ('tags', 'groups'):
                query = self._filter_by_tags_or_groups(field, query, terms)
            elif hasattr(model.Package, field):
                for term in terms:
                    model_attr = getattr(model.Package, field)
                    query = query.filter(make_like(model_attr, term))
            else:
                query = self._filter_by_extra(field, query, terms)

        # Filter for options
        if self._options.filter_by_downloadable:
            query = query.join('package_resources_all', aliased=True).\
                    filter(sqlalchemy.and_(
                model.PackageResource.state==model.State.ACTIVE,
                model.PackageResource.package_id==model.Package.id))
        if self._options.filter_by_openness:
            if self._open_licenses is None:
                self._update_open_licenses()
            query = query.filter(model.Package.license_id.in_(self._open_licenses))
        if self._options.order_by:
            if self._options.order_by == 'rank':
                query = query.add_column(sqlalchemy.func.ts_rank_cd(sqlalchemy.text('package_search.search_vector'), sqlalchemy.func.plainto_tsquery(all_terms)))
                query = query.order_by(sqlalchemy.text('ts_rank_cd_1 DESC'))
            elif hasattr(model.Package, self._options.order_by):
                model_attr = getattr(model.Package, self._options.order_by)
                query = query.order_by(model_attr)
            else:
                # TODO extras
                raise NotImplemented

        query = query.distinct()
        return query

    def _build_tags_query(self, general_terms):
        query = model.Session.query(model.Tag)
        for term in general_terms:
            query = query.filter(model.Tag.name.contains(term.lower()))
        return query

    def _build_groups_query(self, authorized_package_query, general_terms):
        query = authorized_package_query
        for term in general_terms:
            query = query.filter(model.Group.name.contains(term.lower()))
        return query

    def _run_query(self, query):
        # Run the query
        self._results['count'] = query.count()
        query = query.offset(self._options.offset)
        query = query.limit(self._options.limit)

        results = []
        for result in query:
            if isinstance(result, tuple) and isinstance(result[0], model.DomainObject):
                # This is the case for order_by rank due to the add_column.
                results.append(result[0])
            else:
                results.append(result)
        self._results['results'] = results

    def _filter_by_tags_or_groups(self, field, query, value_list):
        for name in value_list:
            if field == 'tags':
                tag = model.Tag.by_name(name.strip(), autoflush=False)
                if tag:
                    tag_id = tag.id
                    # need to keep joining for each filter
                    # tag should be active hence state_id requirement
                    query = query.join('package_tags', aliased=True).filter(sqlalchemy.and_(
                        model.PackageTag.state==model.State.ACTIVE,
                        model.PackageTag.tag_id==tag_id))
                else:
                    # unknown tag, so torpedo search
                    query = query.filter(model.PackageTag.tag_id==u'\x130')
            elif field == 'groups':
                group = model.Group.by_name(name.strip(), autoflush=False)
                if group:
                    group_id = group.id
                    # need to keep joining for each filter
                    query = query.join('groups', aliased=True).filter(
                        model.Group.id==group_id)
                else:
                    # unknown group, so torpedo search
                    query = query.filter(model.Group.id==u'-1')
                    
        return query
    
    def _filter_by_extra(self, field, query, terms):
        make_like = lambda x,y: x.ilike('%' + y + '%')
        value = '%'.join(terms)
        query = query.join('_extras', aliased=True).filter(
            sqlalchemy.and_(
              model.PackageExtra.state==model.State.ACTIVE,
              model.PackageExtra.key==unicode(field),
            )).filter(make_like(model.PackageExtra.value, value))
        return query
        
    def _update_open_licenses(self):  # Update, or init?
        self._open_licenses = []
        for license in model.Package.get_license_register().values():
            if license and license.isopen():
                self._open_licenses.append(license.id)

    def _format_results(self):
        if not self._options.return_objects:
            if self._options.all_fields:
                results = []
                for entity in self._results['results']:
                    if ENABLE_CACHING:
                        cachekey = u'%s-%s' % (unicode(str(type(entity))), entity.id)
                        result = our_cache.get_value(key=cachekey,
                                createfunc=lambda: entity.as_dict(), expiretime=3600)
                    else:
                        result = entity.as_dict()
                    results.append(result)
                self._results['results'] = results
            else:
                self._results['results'] = [entity.name for entity in self._results['results']]
 
