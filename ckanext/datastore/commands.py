import logging

import ckan.lib.cli as cli
import bin.datastore_setup as setup

log = logging.getLogger(__name__)


class SetupDatastoreCommand(cli.CkanCommand):
    '''Perform commands to set up the datastore.
    Make sure that the datastore URLs are set properly before you run
    these commands.

    Usage::

        paster datastore set-permissions SQL_SUPER_USER

    Where:
        SQL_SUPER_USER is the name of a postgres user with sufficient
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

        self.db_write_url_parts = cli.parse_db_config(
            'ckan.datastore.write_url')
        self.db_read_url_parts = cli.parse_db_config(
            'ckan.datastore.read_url')
        self.db_ckan_url_parts = cli.parse_db_config(
            'sqlalchemy.url')

        write_db = self.db_write_url_parts['db_name']
        read_db = self.db_read_url_parts['db_name']
        assert write_db == read_db,\
            "write and read db have to be the same"

        if len(self.args) != 2:
            print self.usage
            return

        if cmd == 'set-permissions':
            setup.set_permissions(
                pguser=self.args[1],
                ckandb=self.db_ckan_url_parts['db_name'],
                datastoredb=self.db_write_url_parts['db_name'],
                ckanuser=self.db_ckan_url_parts['db_user'],
                writeuser=self.db_write_url_parts['db_user'],
                readonlyuser=self.db_read_url_parts['db_user']
            )
            if self.verbose:
                print 'Set permissions for read-only user: SUCCESS'
        else:
            print self.usage
            log.error('Command "%s" not recognized' % (cmd,))
            return
