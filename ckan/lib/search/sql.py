import logging

import sqlalchemy

from common import SearchBackend, SearchQuery, SearchError
from common import SearchIndex, NoopSearchIndex
from ckan import model
from ckan.model import meta
from ckan import authz

log = logging.getLogger(__name__)


class SqlSearchBackend(SearchBackend):
    
    @property
    def engine(self):
        if not hasattr(self, '__engine'):
            self.__engine = meta.engine
        return self.__engine
        
    def _setup(self):
        self.register(model.Package, PackageSqlSearchIndex, PackageSqlSearchQuery)
        self.register(model.Group, NoopSearchIndex, GroupSqlSearchQuery)
        self.register(model.Tag, NoopSearchIndex, TagSqlSearchQuery)
        self.register(model.PackageResource, NoopSearchIndex, ResourceSqlSearchQuery)
        
        
class SqlSearchQuery(SearchQuery):
    """ Common functions for queries against the DB. """
    
    def _db_query(self, q):
        # Run the query
        self.count = q.count()
        q = q.offset(self.options.get('offset'))
        q = q.limit(self.options.get('limit'))
        
        #print q
        
        self.results = []
        for result in q:
            if isinstance(result, tuple) and isinstance(result[0], model.DomainObject):
                # This is the case for order_by rank due to the add_column.
                self.results.append(result[0])
            else:
                self.results.append(result)


class GroupSqlSearchQuery(SqlSearchQuery):
    """ Search for groups in plain SQL. """
    
    def _run(self):
        if not self.query.terms:
            return
        q = authz.Authorizer().authorized_query(username, model.Group)
        for term in self.query.terms:
            q = query.filter(model.Group.name.contains(term.lower()))
        self._db_query(q)


class TagSqlSearchQuery(SqlSearchQuery):
    """ Search for tags in plain SQL. """

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


class ResourceSqlSearchQuery(SqlSearchQuery):
    """ Search for resources in plain SQL. """

    def _run(self):
        q = model.Session.query(model.PackageResource) # TODO authz
        if self.query.terms:
            raise SearchError('Only field specific terms allowed in resource search.')
        #self._check_options_specified_are_allowed('resource search', ['all_fields', 'offset', 'limit'])
        self.options.ref_entity_with_attr = 'id' # has no name
        resource_fields = model.PackageResource.get_columns()
        for field, terms in self.query.fields.items():
            if isinstance(terms, basestring):
                terms = terms.split()
            if field not in resource_fields:
                raise SearchError('Field "%s" not recognised in Resource search.' % field)
            for term in terms:
                model_attr = getattr(model.PackageResource, field)
                if field == 'hash':                
                    q = q.filter(model_attr.ilike(unicode(term) + '%'))
                else:
                    q = q.filter(model_attr.ilike('%' + unicode(term) + '%'))
        
        order_by = self.options.order_by
        if order_by is not None:
            if hasattr(model.PackageResource, order_by):
                q = q.order_by(getattr(model.PackageResource, order_by))
        self._db_query(q)


class PackageSqlSearchQuery(SqlSearchQuery):
    """ Search for packages using SQL and Postgres' TS full-text search. """

    def _run(self):
        q = authz.Authorizer().authorized_query(self.options.get('username'), model.Package)
        make_like = lambda x,y: x.ilike('%' + y + '%')
        q = q.filter(model.package_search_table.c.package_id==model.Package.id)

        # Full search by general terms (and field specific terms but not by field)
        terms_set = set(self.query.terms)
        terms_set.update(self.query.fields.values())
        all_terms = ' '.join(terms_set)
        
        q = q.filter('package_search.search_vector @@ plainto_tsquery(:terms)')
        q = q.params(terms=all_terms)
        
        # Filter by field specific terms
        for field, terms in self.query.fields.items():
            if field == 'tags':
                q = self._filter_by_tag(q, terms)
                continue
            elif field == 'groups':
                q = self._filter_by_group(q, terms)
                continue
            
            if isinstance(terms, basestring):
                terms = terms.split()
                
            if hasattr(model.Package, field):
                model_attr = getattr(model.Package, field)
                for term in terms:
                    q = q.filter(make_like(model_attr, term))
            else:
                q = self._filter_by_extra(q, field, terms)
        
        # Filter for options
        if self.options.filter_by_downloadable:
            q = q.join('package_resources_all', aliased=True)
            q = q.filter(sqlalchemy.and_(
                model.PackageResource.state==model.State.ACTIVE,
                model.PackageResource.package_id==model.Package.id))
        if self.options.filter_by_openness:
            q = q.filter(model.Package.license_id.in_(self.open_licenses))
        
        order_by = self.options.order_by
        if order_by is not None:
            if order_by == 'rank':
                q = q.add_column(sqlalchemy.func.ts_rank_cd(sqlalchemy.text('package_search.search_vector'), 
                                                            sqlalchemy.func.plainto_tsquery(all_terms)))
                q = q.order_by(sqlalchemy.text('ts_rank_cd_1 DESC'))
            elif hasattr(model.Package, order_by):
                q = q.order_by(getattr(model.Package, order_by))
            else:
                # TODO extras
                raise NotImplemented

        q = q.distinct()
        self._db_query(q)
    
    def _filter_by_tag(self, q, term):
        if not self.options.search_tags:
            return q
        tag = model.Tag.by_name(term, autoflush=False)
        if tag:
            # need to keep joining for each filter
            # tag should be active hence state_id requirement
            q = q.join('package_tags', aliased=True).filter(sqlalchemy.and_(
                model.PackageTag.state==model.State.ACTIVE,
                model.PackageTag.tag_id==tag.id))
        else:
            # unknown tag, so torpedo search
            q = q.filter(model.PackageTag.tag_id==u'\x130')
        return q
        
    def _filter_by_group(self, q, term):
        group = model.Group.by_name(term, autoflush=False)
        if group:
            # need to keep joining for each filter
            q = q.join('groups', aliased=True).filter(
                model.Group.id==group.id)
        else:
            # unknown group, so torpedo search
            q = q.filter(model.Group.id==u'-1')
        return q

    def _filter_by_extra(self, q, field, terms):
        make_like = lambda x,y: x.ilike('%' + y + '%')
        for term in terms:
            q = q.join('_extras', aliased=True)
            q = q.filter(model.PackageExtra.state==model.State.ACTIVE)
            q = q.filter(model.PackageExtra.key==unicode(field))
            q = q.filter(make_like(model.PackageExtra.value, term))
        return q
        

class SqlSearchIndex(SearchIndex): pass


class PackageSqlSearchIndex(SqlSearchIndex):
    
    def _make_vector(self, pkg_dict):
        if isinstance(pkg_dict['tags'], (list, tuple)):
            pkg_dict['tags'] = ' '.join(pkg_dict['tags'])
        if isinstance(pkg_dict['groups'], (list, tuple)):
            pkg_dict['groups'] = ' '.join(pkg_dict['groups'])

        document_a = u' '.join((pkg_dict['name'] or u'', pkg_dict['title'] or u''))
        document_b_items = []
        for field_name in ['notes', 'tags', 'groups', 'author', 'maintainer']:
            val = pkg_dict.get(field_name)
            if val:
                document_b_items.append(val)
        extras = pkg_dict.get('extras', {})
        for key, value in extras.items():
            if value is not None:
                document_b_items.append(unicode(value))
        document_b = u' '.join(document_b_items)

        # Create weighted vector
        vector_sql = 'setweight(to_tsvector(%s), \'A\') || setweight(to_tsvector(%s), \'D\')'
        params = [document_a.encode('utf8'), document_b.encode('utf8')]
        return vector_sql, params
    
    def _print_lexemes(self, pkg_dict):
        sql = "SELECT package_id, search_vector FROM package_search WHERE package_id = %s"
        res = self.backend.engine.execute(sql, pkg_dict['id'])
        print res.fetchall()
        res.close()
    
    def insert_dict(self, pkg_dict):
        vector_sql, params = self._make_vector(pkg_dict)
        sql = "INSERT INTO package_search VALUES (%%s, %s)" % vector_sql
        params = [pkg_dict['id']] + params
        res = self.backend.engine.execute(sql, params)
        res.close()
        log.debug("Indexed %s" % pkg_dict.get('name'))
    
    def update_dict(self, pkg_dict):
        vector_sql, params = self._make_vector(pkg_dict)
        sql = "UPDATE package_search SET search_vector=%s WHERE package_id=%%s" % vector_sql
        params.append(pkg_dict['id'])
        res = self.backend.engine.execute(sql, params)
        res.close()
        log.debug("Updated index for %s" % pkg_dict.get('name'))
        
    def remove_dict(self, pkg_dict):
        # This is currently handled by the foreign key constraint on package_id. 
        # Once we remove that constraint, manual removal will become necessary.
        pass
        
    def clear(self):
        res = self.backend.engine.execute("DELETE FROM package_search WHERE 1=1")
        res.close()
