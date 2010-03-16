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
import subprocess

from pylons import config

assert config.has_key('here'), 'ERROR: You need to run nosetests with option: --with-pylons=testmigrate.ini'

CONFIG_FILE = 'testmigrate.ini'
DB_NAME = 'ckantestmigrate'
DB_USER = 'tester'
TEST_DUMPS_PATH = os.path.join(config['here'], 'ckan/migration/tests/test_dumps')
RESTORE_FILEPATH = config['test_migration_db_dump']

class TestMigrationBase(object):
    psqlbase = 'export PGPASSWORD=pass && psql -q -h localhost --user %s %s' % (DB_USER, DB_NAME)

    @classmethod
    def setup_db(self, pg_dump_file=None):
        if not pg_dump_file:
            pg_dump_file = RESTORE_FILEPATH
        assert pg_dump_file
        self.run(self.psqlbase + ' -o /tmp/psql.tmp < %s' % pg_dump_file)

    @classmethod
    def run(self, cmd, ok_to_fail=False):
        try:
            proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output = proc.communicate()
            if len(output)==2:
                output = '\n'.join(output)
            else:
                output = repr(output)
            retcode = proc.wait()
            print output
            if not ok_to_fail:
                assert retcode == 0, 'Error %i running "%s": %s' % (retcode, cmd, output)
        except OSError, e:
            print 'Error running "%s":' % cmd, e
            print output
            if not ok_to_fail:
                assert retcode == 0, 'Error %i running "%s": %s' % (retcode, cmd, output)

    @classmethod
    def paster(self, paster_cmd):
        self.run('paster %s --config=%s' % (paster_cmd, CONFIG_FILE))

    @classmethod
    def rebuild_db(self):
        print "Need sudo to rebuild the database"
        self.run('sudo -u postgres dropdb %s' % DB_NAME, ok_to_fail=True)
        self.run('sudo -u postgres createdb --owner %s %s' % (DB_USER, DB_NAME))

# Recreate database before all tests.
# Note this complains of current users of the database if you run it
# having created a session, so only do it once.
TestMigrationBase.rebuild_db()

