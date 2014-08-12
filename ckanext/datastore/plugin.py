import logging
import pylons

import ckan.plugins as p
import ckanext.datastore.logic.action as action
import ckanext.datastore.logic.auth as auth
import ckanext.datastore.db as db
import ckan.logic as logic
import ckan.model as model

log = logging.getLogger(__name__)
_get_or_bust = logic.get_or_bust


def _is_legacy_mode(config):
    '''
        Decides if the DataStore should run on legacy mode

        Returns True if `ckan.datastore.read_url` is not set in the provided
        config object or CKAN is running on Postgres < 9.x
    '''
    write_url = config.get('ckan.datastore.write_url')

    engine = db._get_engine({}, {'connection_url': write_url})
    connection = engine.connect()

    return (not config.get('ckan.datastore.read_url') or
            not db._pg_version_is_at_least(connection, '9.0'))


class DatastoreException(Exception):
    pass


class DatastorePlugin(p.SingletonPlugin):
    p.implements(p.IConfigurable, inherit=True)
    p.implements(p.IActions)
    p.implements(p.IAuthFunctions)

    legacy_mode = False

    def configure(self, config):
        self.config = config
        # check for ckan.datastore.write_url and ckan.datastore.read_url
        if (not 'ckan.datastore.write_url' in config):
            error_msg = 'ckan.datastore.write_url not found in config'
            raise DatastoreException(error_msg)

        # Legacy mode means that we have no read url. Consequently sql search is not
        # available and permissions do not have to be changed. In legacy mode, the
        # datastore runs on PG prior to 9.0 (for example 8.4).
        self.legacy_mode = _is_legacy_mode(self.config)

        # Check whether we are running one of the paster commands which means
        # that we should ignore the following tests.
        import sys
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

        if not model.engine_is_pg():
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

        ## Do light wrapping around action function to add datastore_active
        ## to resource dict.  Not using IAction extension as this prevents
        ## other plugins from having a custom resource_read.

        # Make sure actions are cached
        resource_show = p.toolkit.get_action('resource_show')

        def new_resource_show(context, data_dict):
            engine = db._get_engine(
                context,
                {'connection_url': self.read_url}
            )
            new_data_dict = resource_show(context, data_dict)
            try:
                connection = engine.connect()
                result = connection.execute(
                    'SELECT 1 FROM "_table_metadata" WHERE name = %s AND alias_of IS NULL',
                    new_data_dict['id']
                ).fetchone()
                if result:
                    new_data_dict['datastore_active'] = True
                else:
                    new_data_dict['datastore_active'] = False
            finally:
                connection.close()
            return new_data_dict

        ## Make sure do not run many times if configure is called repeatedly
        ## as in tests.
        if not hasattr(resource_show, '_datastore_wrapped'):
            new_resource_show._datastore_wrapped = True
            logic._actions['resource_show'] = new_resource_show

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

        # in legacy mode, the read and write url are ths same (both write url)
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
            connection = db._get_engine(None,
                                        {'connection_url': url}).connect()
            sql = u"SELECT has_schema_privilege('public', 'CREATE')"
            is_writable = connection.execute(sql).first()[0]
            if is_writable:
                return False
        return True

    def _same_ckan_and_datastore_db(self):
        '''Returns True if the CKAN and DataStore db are the same'''
        return self._get_db_from_url(self.ckan_url) == self._get_db_from_url(self.read_url)

    def _get_db_from_url(self, url):
        return url[url.rindex("@"):]

    def _same_read_and_write_url(self):
        return self.write_url == self.read_url

    def _read_connection_has_correct_privileges(self):
        ''' Returns True if the right permissions are set for the read only user.
        A table is created by the write user to test the read only user.
        '''
        write_connection = db._get_engine(None,
            {'connection_url': self.write_url}).connect()
        read_connection = db._get_engine(None,
            {'connection_url': self.read_url}).connect()

        drop_foo_sql = u'DROP TABLE IF EXISTS _foo'

        write_connection.execute(drop_foo_sql)

        try:
            write_connection.execute(u'CREATE TABLE _foo ()')
            for privilege in ['INSERT', 'UPDATE', 'DELETE']:
                test_privilege_sql = u"SELECT has_table_privilege('_foo', '{privilege}')"
                sql = test_privilege_sql.format(privilege=privilege)
                have_privilege = read_connection.execute(sql).first()[0]
                if have_privilege:
                    return False
        finally:
            write_connection.execute(drop_foo_sql)
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
        connection = db._get_engine(None,
            {'connection_url': pylons.config['ckan.datastore.write_url']}).connect()
        connection.execute(create_alias_table_sql)

    def get_actions(self):
        actions = {'datastore_create': action.datastore_create,
                   'datastore_upsert': action.datastore_upsert,
                   'datastore_delete': action.datastore_delete,
                   'datastore_search': action.datastore_search}
        if not self.legacy_mode:
            actions['datastore_search_sql'] = action.datastore_search_sql
        return actions

    def get_auth_functions(self):
        return {'datastore_create': auth.datastore_create,
                'datastore_upsert': auth.datastore_upsert,
                'datastore_delete': auth.datastore_delete,
                'datastore_search': auth.datastore_search}
