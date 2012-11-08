import logging
import pylons
from sqlalchemy.exc import ProgrammingError
import ckan.plugins as p
import ckanext.datastore.logic.action as action
import ckanext.datastore.logic.auth as auth
import ckanext.datastore.db as db
import ckan.logic as logic

log = logging.getLogger(__name__)
_get_or_bust = logic.get_or_bust


class DatastoreException(Exception):
    pass


class DatastorePlugin(p.SingletonPlugin):
    '''
    Datastore plugin.
    '''
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
        self.legacy_mode = 'ckan.datastore.read_url' not in self.config

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
        else:
            self.read_url = self.config['ckan.datastore.read_url']

        if not self._is_read_only_database():
            # Make sure that the right permissions are set
            # so that no harmful queries can be made
            if not ('debug' in config and config['debug']):
                self._check_separate_db()
            if self.legacy_mode:
                log.warn('Legacy mode active. The sql search will not be available.')
            else:
                self._check_read_permissions()

            self._create_alias_table()
        else:
            log.warn("We detected that CKAN is running on a read only database. "
                "Permission checks and _table_metadata creation are skipped."
                "Make sure that replication is properly set-up.")

        ## Do light wrapping around action function to add datastore_active
        ## to resource dict.  Not using IAction extension as this prevents other plugins
        ## from having a custom resource_read.

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

    def _is_read_only_database(self):
        read_only_database = True
        for url in [self.ckan_url, self.write_url, self.read_url]:
            connection = db._get_engine(None,
                {'connection_url': url}).connect()
            trans = connection.begin()
            try:
                sql = u"CREATE TABLE test_readonly(id INTEGER);"
                connection.execute(sql)
            except ProgrammingError, e:
                if 'permission denied' in str(e) or 'read-only transaction' in str(e):
                    pass
                else:
                    raise
            else:
                read_only_database = False
            finally:
                trans.rollback()
        return read_only_database

    def _check_separate_db(self):
        '''
        Make sure the datastore is on a separate db. Otherwise one could access
        all internal tables via the api.
        '''

        if self.write_url == self.read_url:
            raise Exception("The write and read-only database connection url are the same.")

        if self._get_db_from_url(self.ckan_url) == self._get_db_from_url(self.read_url):
            raise Exception("The CKAN and datastore database are the same.")

    def _get_db_from_url(self, url):
        return url[url.rindex("@"):]

    def _check_read_permissions(self):
        '''
        Check whether the right permissions are set for the read only user.
        A table is created by the write user to test the read only user.
        '''
        write_connection = db._get_engine(None,
            {'connection_url': self.write_url}).connect()
        write_connection.execute(u"DROP TABLE IF EXISTS public._foo;"
            u"CREATE TABLE public._foo (id INTEGER, name VARCHAR)")

        read_connection = db._get_engine(None,
            {'connection_url': self.read_url}).connect()

        statements = [
            u"CREATE TABLE public._bar (id INTEGER, name VARCHAR)",
            u"INSERT INTO public._foo VALUES (1, 'okfn')"
        ]

        try:
            for sql in statements:
                read_trans = read_connection.begin()
                try:
                    read_connection.execute(sql)
                except ProgrammingError, e:
                    if 'permission denied' not in str(e):
                        raise
                else:
                    log.info("Connection url {0}".format(self.read_url))
                    if 'debug' in self.config and self.config['debug']:
                        log.critical("We have write permissions on the read-only database.")
                    else:
                        raise Exception("We have write permissions on the read-only database.")
                finally:
                    read_trans.rollback()
        except Exception:
            raise
        finally:
            write_connection.execute("DROP TABLE _foo")

    def _create_alias_table(self):
        mapping_sql = '''
            SELECT DISTINCT
                substr(md5(concat(dependee.relname, dependent.relname)), 0, 17) AS "_id",
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
