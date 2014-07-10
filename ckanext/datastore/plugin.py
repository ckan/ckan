import sys
import logging
import shlex

import sqlalchemy.engine.url as sa_url

import ckan.plugins as p
import ckan.logic as logic
import ckan.model as model
import ckanext.datastore.logic.action as action
import ckanext.datastore.logic.auth as auth
import ckanext.datastore.db as db
import ckanext.datastore.interfaces as interfaces
import ckanext.datastore.helpers as datastore_helpers


log = logging.getLogger(__name__)
_get_or_bust = logic.get_or_bust

DEFAULT_FORMATS = []

ValidationError = p.toolkit.ValidationError


class DatastoreException(Exception):
    pass


class DatastorePlugin(p.SingletonPlugin):
    p.implements(p.IConfigurable, inherit=True)
    p.implements(p.IActions)
    p.implements(p.IAuthFunctions)
    p.implements(p.IResourceUrlChange)
    p.implements(p.IDomainObjectModification, inherit=True)
    p.implements(p.IRoutes, inherit=True)
    p.implements(p.IResourceController, inherit=True)
    p.implements(interfaces.IDatastore, inherit=True)

    legacy_mode = False
    resource_show_action = None

    def __new__(cls, *args, **kwargs):
        idatastore_extensions = p.PluginImplementations(interfaces.IDatastore)
        idatastore_extensions = idatastore_extensions.extensions()

        if idatastore_extensions and idatastore_extensions[0].__class__ != cls:
            msg = ('The "datastore" plugin must be the first IDatastore '
                   'plugin loaded. Change the order it is loaded in '
                   '"ckan.plugins" in your CKAN .ini file and try again.')
            raise DatastoreException(msg)

        return super(cls, cls).__new__(cls, *args, **kwargs)

    def configure(self, config):
        self.config = config
        # check for ckan.datastore.write_url and ckan.datastore.read_url
        if (not 'ckan.datastore.write_url' in config):
            error_msg = 'ckan.datastore.write_url not found in config'
            raise DatastoreException(error_msg)

        # Legacy mode means that we have no read url. Consequently sql search is not
        # available and permissions do not have to be changed. In legacy mode, the
        # datastore runs on PG prior to 9.0 (for example 8.4).
        self.legacy_mode = 'ckan.datastore.read_url' not in self.config

        datapusher_formats = config.get('datapusher.formats', '').split()
        self.datapusher_formats = datapusher_formats or DEFAULT_FORMATS

        # Check whether we are running one of the paster commands which means
        # that we should ignore the following tests.
        if sys.argv[0].split('/')[-1] == 'paster' and 'datastore' in sys.argv[1:]:
            log.warn('Omitting permission checks because you are '
                     'running paster commands.')
            return

        self.ckan_url = self.config['sqlalchemy.url']
        self.write_url = self.config['ckan.datastore.write_url']
        if self.legacy_mode:
            self.read_url = self.write_url
            log.warn('Legacy mode active. '
                     'The sql search will not be available.')
        else:
            self.read_url = self.config['ckan.datastore.read_url']

        self.read_engine = db._get_engine(
            {'connection_url': self.read_url})
        if not model.engine_is_pg(self.read_engine):
            log.warn('We detected that you do not use a PostgreSQL '
                     'database. The DataStore will NOT work and DataStore '
                     'tests will be skipped.')
            return

        if self._is_read_only_database():
            log.warn('We detected that CKAN is running on a read '
                     'only database. Permission checks and the creation '
                     'of _table_metadata are skipped.')
        else:
            self._check_urls_and_permissions()
            self._create_alias_table()

    def notify(self, entity, operation=None):
        if not isinstance(entity, model.Package) or self.legacy_mode:
            return
        # if a resource is new, it cannot have a datastore resource, yet
        if operation == model.domain_object.DomainObjectOperation.changed:
            context = {'model': model, 'ignore_auth': True}
            if entity.private:
                func = p.toolkit.get_action('datastore_make_private')
            else:
                func = p.toolkit.get_action('datastore_make_public')
            for resource in entity.resources:
                try:
                    func(context, {
                        'connection_url': self.write_url,
                        'resource_id': resource.id})
                except p.toolkit.ObjectNotFound:
                    pass

    def _log_or_raise(self, message):
        if self.config.get('debug'):
            log.critical(message)
        else:
            raise DatastoreException(message)

    def _check_urls_and_permissions(self):
        # Make sure that the right permissions are set
        # so that no harmful queries can be made

        if self._same_ckan_and_datastore_db():
            self._log_or_raise('CKAN and DataStore database '
                               'cannot be the same.')

        # in legacy mode, the read and write url are the same (both write url)
        # consequently the same url check and and write privilege check
        # don't make sense
        if not self.legacy_mode:
            if self._same_read_and_write_url():
                self._log_or_raise('The write and read-only database '
                                   'connection urls are the same.')

            if not self._read_connection_has_correct_privileges():
                self._log_or_raise('The read-only user has write privileges.')

    def _is_read_only_database(self):
        ''' Returns True if no connection has CREATE privileges on the public
        schema. This is the case if replication is enabled.'''
        for url in [self.ckan_url, self.write_url, self.read_url]:
            connection = db._get_engine({'connection_url': url}).connect()
            try:
                sql = u"SELECT has_schema_privilege('public', 'CREATE')"
                is_writable = connection.execute(sql).first()[0]
            finally:
                connection.close()
            if is_writable:
                return False
        return True

    def _same_ckan_and_datastore_db(self):
        '''Returns True if the CKAN and DataStore db are the same'''
        return self._get_db_from_url(self.ckan_url) == self._get_db_from_url(self.read_url)

    def _get_db_from_url(self, url):
        db_url = sa_url.make_url(url)
        return db_url.host, db_url.port, db_url.database

    def _same_read_and_write_url(self):
        return self.write_url == self.read_url

    def _read_connection_has_correct_privileges(self):
        ''' Returns True if the right permissions are set for the read
        only user. A table is created by the write user to test the
        read only user.
        '''
        write_connection = db._get_engine(
            {'connection_url': self.write_url}).connect()
        read_connection_user = sa_url.make_url(self.read_url).username

        drop_foo_sql = u'DROP TABLE IF EXISTS _foo'

        write_connection.execute(drop_foo_sql)

        try:
            write_connection.execute(u'CREATE TEMP TABLE _foo ()')
            for privilege in ['INSERT', 'UPDATE', 'DELETE']:
                test_privilege_sql = u"SELECT has_table_privilege(%s, '_foo', %s)"
                have_privilege = write_connection.execute(
                    test_privilege_sql, (read_connection_user, privilege)).first()[0]
                if have_privilege:
                    return False
        finally:
            write_connection.execute(drop_foo_sql)
            write_connection.close()
        return True

    def _create_alias_table(self):
        mapping_sql = '''
            SELECT DISTINCT
                substr(md5(dependee.relname || COALESCE(dependent.relname, '')), 0, 17) AS "_id",
                dependee.relname AS name,
                dependee.oid AS oid,
                dependent.relname AS alias_of
                -- dependent.oid AS oid
            FROM
                pg_class AS dependee
                LEFT OUTER JOIN pg_rewrite AS r ON r.ev_class = dependee.oid
                LEFT OUTER JOIN pg_depend AS d ON d.objid = r.oid
                LEFT OUTER JOIN pg_class AS dependent ON d.refobjid = dependent.oid
            WHERE
                (dependee.oid != dependent.oid OR dependent.oid IS NULL) AND
                (dependee.relname IN (SELECT tablename FROM pg_catalog.pg_tables)
                    OR dependee.relname IN (SELECT viewname FROM pg_catalog.pg_views)) AND
                dependee.relnamespace = (SELECT oid FROM pg_namespace WHERE nspname='public')
            ORDER BY dependee.oid DESC;
        '''
        create_alias_table_sql = u'CREATE OR REPLACE VIEW "_table_metadata" AS {0}'.format(mapping_sql)
        try:
            connection = db._get_engine(
                {'connection_url': self.write_url}).connect()
            connection.execute(create_alias_table_sql)
        finally:
            connection.close()

    def get_actions(self):
        actions = {'datastore_create': action.datastore_create,
                   'datastore_upsert': action.datastore_upsert,
                   'datastore_delete': action.datastore_delete,
                   'datastore_search': action.datastore_search,
                  }
        if not self.legacy_mode:
            actions.update({
                'datastore_search_sql': action.datastore_search_sql,
                'datastore_make_private': action.datastore_make_private,
                'datastore_make_public': action.datastore_make_public})
        return actions

    def get_auth_functions(self):
        return {'datastore_create': auth.datastore_create,
                'datastore_upsert': auth.datastore_upsert,
                'datastore_delete': auth.datastore_delete,
                'datastore_search': auth.datastore_search,
                'datastore_search_sql': auth.datastore_search_sql,
                'datastore_change_permissions': auth.datastore_change_permissions}

    def before_map(self, m):
        m.connect('/datastore/dump/{resource_id}',
                  controller='ckanext.datastore.controller:DatastoreController',
                  action='dump')
        return m

    def before_show(self, resource_dict):
        # Modify the resource url of datastore resources so that
        # they link to the datastore dumps.
        if resource_dict.get('url_type') == 'datastore':
            resource_dict['url'] = p.toolkit.url_for(
                controller='ckanext.datastore.controller:DatastoreController',
                action='dump', resource_id=resource_dict['id'])

        connection = None
        try:
            connection = self.read_engine.connect()
            result = connection.execute(
                'SELECT 1 FROM "_table_metadata" WHERE name = %s AND alias_of IS NULL',
                resource_dict['id']
            ).fetchone()
            if result:
                resource_dict['datastore_active'] = True
            else:
                resource_dict['datastore_active'] = False
        finally:
            if connection:
                connection.close()
        return resource_dict

    def datastore_validate(self, context, data_dict, column_names):
        fields = data_dict.get('fields')
        if fields:
            data_dict['fields'] = list(set(fields) - set(column_names))

        filters = data_dict.get('filters', {})
        for key in filters.keys():
            if key in column_names:
                del filters[key]

        q = data_dict.get('q')
        if q:
            if isinstance(q, basestring):
                del data_dict['q']
            elif isinstance(q, dict):
                for key in q.keys():
                    if key in column_names and isinstance(q[key], basestring):
                        del q[key]

        language = data_dict.get('language')
        if language:
            if isinstance(language, basestring):
                del data_dict['language']

        plain = data_dict.get('plain')
        if plain:
            if isinstance(plain, bool):
                del data_dict['plain']

        sort_clauses = data_dict.get('sort')
        if sort_clauses:
            invalid_clauses = [c for c in sort_clauses
                               if not self._is_valid_sort(c, column_names)]
            data_dict['sort'] = invalid_clauses

        limit = data_dict.get('limit')
        if limit:
            is_positive_int = datastore_helpers.validate_int(limit,
                                                             non_negative=True)
            is_all = isinstance(limit, basestring) and limit.lower() == 'all'
            if is_positive_int or is_all:
                del data_dict['limit']

        offset = data_dict.get('offset')
        if offset:
            is_positive_int = datastore_helpers.validate_int(offset,
                                                             non_negative=True)
            if is_positive_int:
                del data_dict['offset']

        return data_dict

    def _is_valid_sort(self, clause, column_names):
        clause = clause.encode('utf-8')
        clause_parts = shlex.split(clause)

        if len(clause_parts) == 1:
            field, sort = clause_parts[0], 'asc'
        elif len(clause_parts) == 2:
            field, sort = clause_parts
        else:
            return False

        field, sort = unicode(field, 'utf-8'), unicode(sort, 'utf-8')

        if field not in column_names:
            return False
        if sort.lower() not in ('asc', 'desc'):
            return False

        return True

    def datastore_delete(self, context, data_dict, column_names, query_dict):
        query_dict['where'] += self._where(data_dict, column_names)
        return query_dict

    def datastore_search(self, context, data_dict, column_names, query_dict):
        fields = data_dict.get('fields')

        if fields:
            field_ids = datastore_helpers.get_list(fields)
        else:
            field_ids = column_names

        ts_query, rank_column = self._textsearch_query(data_dict)
        limit = data_dict.get('limit', 100)
        offset = data_dict.get('offset', 0)

        sort = self._sort(data_dict)
        where = self._where(data_dict)

        select_cols = [u'"{0}"'.format(field_id) for field_id in field_ids] +\
                      [u'count(*) over() as "_full_count" %s' % rank_column]

        query_dict['select'] += select_cols
        query_dict['ts_query'] = ts_query
        query_dict['sort'] += sort
        query_dict['where'] += where
        query_dict['limit'] = limit
        query_dict['offset'] = offset

        return query_dict

    def _where(self, data_dict):
        filters = data_dict.get('filters', {})
        clauses = []
        for field, value in filters.iteritems():
            clause = (u'"{0}" = %s'.format(field), value)
            clauses.append(clause)

        # add full-text search where clause
        q = data_dict.get('q')
        if q:
            if isinstance(q, basestring):
                clause = (u'_full_text @@ {0}'.format(self._ts_query_alias()),)
                clauses.append(clause)
            elif isinstance(q, dict):
                for field, value in q.iteritems():
                    query_field = self._ts_query_alias(field)
                    clause_str = u'"{0}" @@ {1}'.format(field, query_field)
                    clause = (clause_str, value)
                    clauses.append(clause)

        return clauses

    def _sort(self, data_dict):
        sort = data_dict.get('sort')
        if not sort:
            q = data_dict.get('q')
            if q:
                if isinstance(q, basestring):
                    return [self._ts_rank_alias()]
                elif isinstance(q, dict):
                    return [self._ts_rank_alias(field) for field in q]
            else:
                return []

        clauses = datastore_helpers.get_list(sort, False)

        clause_parsed = []

        for clause in clauses:
            clause = clause.encode('utf-8')
            clause_parts = shlex.split(clause)
            if len(clause_parts) == 1:
                field, sort = clause_parts[0], 'asc'
            elif len(clause_parts) == 2:
                field, sort = clause_parts

            field, sort = unicode(field, 'utf-8'), unicode(sort, 'utf-8')

            clause_parsed.append(u'"{0}" {1}'.format(field, sort))

        return clause_parsed

    def _textsearch_query(self, data_dict):
        q = data_dict.get('q')
        lang = data_dict.get(u'language', u'english')

        if not q:
            return '', ''

        statements = []
        rank_columns = []
        plain = data_dict.get('plain', True)
        if isinstance(q, basestring):
            query, rank = self._build_query_and_rank_statements(lang,
                                                                q,
                                                                plain)
            statements.append(query)
            rank_columns.append(rank)
        elif isinstance(q, dict):
            for field, value in q.iteritems():
                query, rank = self._build_query_and_rank_statements(lang,
                                                                    value,
                                                                    plain,
                                                                    field)
                statements.append(query)
                rank_columns.append(rank)

        statements_str = ', ' + ', '.join(statements)
        rank_columns_str = ', ' + ', '.join(rank_columns)
        return statements_str, rank_columns_str

    def _build_query_and_rank_statements(self, lang, query, plain, field=None):
        query_alias = self._ts_query_alias(field)
        rank_alias = self._ts_rank_alias(field)
        if plain:
            statement = u"plainto_tsquery('{lang}', '{query}') {alias}"
        else:
            statement = u"to_tsquery('{lang}', '{query}') {alias}"
        rank_statement = u'ts_rank(_full_text, {query_alias}, 32) AS {alias}'
        statement = statement.format(lang=lang, query=query, alias=query_alias)
        rank_statement = rank_statement.format(query_alias=query_alias,
                                               alias=rank_alias)
        return statement, rank_statement

    def _ts_query_alias(self, field=None):
        query_alias = u'query'
        if field:
            query_alias += u' ' + field
        return u'"{0}"'.format(query_alias)

    def _ts_rank_alias(self, field=None):
        rank_alias = u'rank'
        if field:
            rank_alias += u' ' + field
        return u'"{0}"'.format(rank_alias)
