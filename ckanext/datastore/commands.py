import re
from ckan.lib.cli import CkanCommand

import logging
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
CREATE USER "{readonlyuser}" NOSUPERUSER NOCREATEDB NOCREATEROLE LOGIN;

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


class SetupDatastoreCommand(CkanCommand):
    '''Perform commands to set up the datastore.
    Make sure that the datastore urls are set properly before you run these commands.

    Usage::

        paster datastore create-db <sql-user-user>
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

        self.urlparts_w = self._get_db_config('ckan.datastore.write_url')
        self.urlparts_r = self._get_db_config('ckan.datastore.read_url')
        self.urlparts_c = self._get_db_config('sqlalchemy.url')

        assert self.urlparts_w['db_name'] == self.urlparts_r['db_name'], "write and read db should be the same"

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

    def _get_db_config(self, name):
        from pylons import config
        url = config[name]
        # e.g. 'postgres://tester:pass@localhost/ckantest3'
        db_details_match = re.match('^\s*(?P<db_type>\w*)://(?P<db_user>[^:]*):?(?P<db_pass>[^@]*)@(?P<db_host>[^/:]*):?(?P<db_port>[^/]*)/(?P<db_name>[\w.-]*)', url)
        if not db_details_match:
            raise Exception('Could not extract db details from url: %r' % url)
        db_details = db_details_match.groupdict()
        return db_details

    def _run_cmd(self, command_line):
        import subprocess
        retcode = subprocess.call(command_line, shell=True)
        if retcode != 0:
            raise SystemError('Command exited with errorcode: %i' % retcode)

    def _run_sql(self, sql, as_sql_user, database='postgres'):
        if self.verbose:
            print "Executing: \n#####\n", sql, "\n####\nOn database:", database
        if not self.simulate:
            self._run_cmd("psql --username='{username}' --dbname='{database}' -c '{sql}' -W".format(
                username=as_sql_user,
                database=database,
                sql=sql
            )) 

    def create_db(self):
        sql = "create database {0}".format(self.urlparts_w['db_name'])
        self._run_sql(sql, as_sql_user=self.sql_superuser)

    def create_read_only_user(self):
        sql = read_only_user_sql.format(
            maindb=self.urlparts_c['db_name'],
            datastore=self.urlparts_w['db_name'],
            ckanuser=self.urlparts_c['db_user'],
            readonlyuser=self.urlparts_r['db_user'],
            writeuser=self.urlparts_w['db_user'])
        self._run_sql(sql,
                      as_sql_user=self.sql_superuser,
                      database=self.urlparts_w['db_name'])

