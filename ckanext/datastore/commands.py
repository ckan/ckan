import re
import sys
import logging

import ckan.lib.cli as cli

log = logging.getLogger(__name__)


read_only_user_sql = '''
-- revoke permissions for the new user
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
REVOKE USAGE ON SCHEMA public FROM PUBLIC;

GRANT CREATE ON SCHEMA public TO "{ckanuser}";
GRANT USAGE ON SCHEMA public TO "{ckanuser}";

GRANT CREATE ON SCHEMA public TO "{writeuser}";
GRANT USAGE ON SCHEMA public TO "{writeuser}";

-- create new read only user
CREATE USER "{readonlyuser}" {with_password} NOSUPERUSER NOCREATEDB NOCREATEROLE LOGIN;

-- take connect permissions from main db
REVOKE CONNECT ON DATABASE "{maindb}" FROM "{readonlyuser}";

-- grant select permissions for read-only user
GRANT CONNECT ON DATABASE "{datastore}" TO "{readonlyuser}";
GRANT USAGE ON SCHEMA public TO "{readonlyuser}";

-- grant access to current tables and views
GRANT SELECT ON ALL TABLES IN SCHEMA public TO "{readonlyuser}";

-- grant access to new tables and views by default
ALTER DEFAULT PRIVILEGES FOR USER "{ckanuser}" IN SCHEMA public
   GRANT SELECT ON TABLES TO "{readonlyuser}";
'''


class SetupDatastoreCommand(cli.CkanCommand):
    '''Perform commands to set up the datastore.
    Make sure that the datastore urls are set properly before you run these commands.

    Usage::

        paster datastore create-db <sql-super-user>
        paster datastore create-read-only-user <sql-super-user>

    Where:
        <sql-super-user> is the name of a postgres user with sufficient
                         permissions to create new tables, users, and grant
                         and revoke new permissions.  Typically, this would
                         be the "postgres" user.

    '''
    summary = __doc__.split('\n')[0]
    usage = __doc__

    def __init__(self, name):

        super(SetupDatastoreCommand, self).__init__(name)

    def command(self):
        '''
        Parse command line arguments and call appropriate method.
        '''
        if not self.args or self.args[0] in ['--help', '-h', 'help']:
            print SetupDatastoreCommand.__doc__
            return

        cmd = self.args[0]
        self._load_config()

        self.db_write_url_parts = cli.parse_db_config('ckan.datastore.write_url')
        self.db_read_url_parts = cli.parse_db_config('ckan.datastore.read_url')
        self.db_ckan_url_parts = cli.parse_db_config('sqlalchemy.url')

        assert self.db_write_url_parts['db_name'] == self.db_read_url_parts['db_name'], "write and read db should be the same"

        if cmd == 'create-db':
            if len(self.args) != 2:
                print self.usage
                return
            self.sql_superuser = self.args[1]
            self.create_db()
            if self.verbose:
                print 'Creating DB: SUCCESS'
        elif cmd == 'create-read-only-user':
            if len(self.args) != 2:
                print self.usage
                return
            self.sql_superuser = self.args[1]
            self.create_read_only_user()
            if self.verbose:
                print 'Creating read-only user: SUCCESS'
        else:
            print self.usage
            log.error('Command "%s" not recognized' % (cmd,))
            return

    def _run_cmd(self, command_line, inputstring=''):
        import subprocess
        p = subprocess.Popen(
            command_line, shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        stdout_value, stderr_value = p.communicate(input=inputstring)
        if stderr_value:
            print '\nAn error occured: {0}'.format(stderr_value)
            sys.exit(1)

    def _run_sql(self, sql, as_sql_user, database='postgres'):
        if self.verbose:
            print "Executing: \n#####\n", sql, "\n####\nOn database:", database
        if not self.simulate:
            self._run_cmd("psql --username='{username}' --dbname='{database}' -W".format(
                username=as_sql_user,
                database=database
            ), inputstring=sql)

    def create_db(self):
        sql = "create database {0}".format(self.db_write_url_parts['db_name'])
        self._run_sql(sql, as_sql_user=self.sql_superuser)

    def create_read_only_user(self):
        password = self.db_read_url_parts['db_pass']
        self.validate_password(password)
        sql = read_only_user_sql.format(
            maindb=self.db_ckan_url_parts['db_name'],
            datastore=self.db_write_url_parts['db_name'],
            ckanuser=self.db_ckan_url_parts['db_user'],
            readonlyuser=self.db_read_url_parts['db_user'],
            with_password="WITH PASSWORD '{0}'".format(password) if password else "",
            writeuser=self.db_write_url_parts['db_user'])
        self._run_sql(sql,
                      as_sql_user=self.sql_superuser,
                      database=self.db_write_url_parts['db_name'])

    def validate_password(self, password):
        if "'" in password:
            raise ValueError("Passwords cannot contain '")
