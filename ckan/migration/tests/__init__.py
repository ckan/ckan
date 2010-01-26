'''
To setup for tests:

1. Create a config file for these tests
    $ paster make-config ckan testmigrate.ini

2. Edit config file to point to a new test database and tell it about a dump
   of the database to test migration from.
      sqlalchemy.url = postgres://tester:pass@localhost/ckantestmigrate
      test_migration_db_dump = ~/db_backup/ckan.net/ckan.net.2010-01-13.pg_dump

To run a test:
    $ nosetests ckan/migration/tests/test_15.py --with-pylons=testmigrate.ini


'''
import os
import sys

from pylons import config

CONFIG_FILE = 'testmigrate.ini'
DB_NAME = 'ckantestmigrate'
DB_USER = 'tester'

class TestMigrationBase(object):
    psqlbase = 'export PGPASSWORD=pass && psql -q -h localhost --user %s %s' % (DB_USER, DB_NAME)

    @classmethod
    def setup_db(self):
        restore_filepath = config['test_migration_db_dump']
        self.run('sudo -u postgres dropdb %s' % DB_NAME, ok_to_fail=True)
        self.run('sudo -u postgres createdb --owner %s %s' % (DB_USER, DB_NAME))
        self.run(self.psqlbase + ' -o /tmp/psql.tmp < %s' % restore_filepath)

    @classmethod
    def run(self, cmd, ok_to_fail=False):
        err = os.system(cmd)
        if not ok_to_fail:
            assert not err, 'Error %i running: %s' % (err, cmd)
