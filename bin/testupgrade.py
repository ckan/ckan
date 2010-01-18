import os
import sys

def simple():
    cmd = 'paster db clean && paster db upgrade && paster db init && paster create-test-data'
    print(cmd)
    print('nosetests ckan/tests/model')

psqlbase = 'export PGPASSWORD=pass && psql -q -h localhost --user tester '
def setup_db(dbname, path_to_backup):
    cmd = 'sudo -u postgres dropdb %s' % dbname
    os.system(cmd)
    cmd = 'sudo -u postgres createdb --owner tester %s' % dbname
    os.system(cmd)
    cmd = psqlbase + dbname + ' < %s' % path_to_backup
    os.system(cmd)

def complex(dbname):
    # run upgrade and test
    # tmp.ini should use dbname
    cmd = 'paster db --config tmp.ini upgrade'
    os.system(cmd)
    cmd = psqlbase + dbname + ' -c "select count(*) from package_resource_revision;"'
    os.system(cmd)
    cmd = psqlbase + dbname + ' -c "select count(*) from package_resource;"'
    os.system(cmd)
    cmd = psqlbase + dbname + ' -c "select * from package_resource join package_resource_revision on package_resource.id = package_resource_revision.continuity_id limit 2;"'
    os.system(cmd)

import optparse
if __name__ == '__main__':
    usage = '''%prog {action}
    '''
    parser = optparse.OptionParser(usage)
    options, args = parser.parse_args()
    action = args[0]
    dbname = 'ckantmp'
    if action == 'setup':
        path_to_backup = '/home/rgrp/db_backup/ckan.net/ckan.net.2010-01-13.2.pg_dump'
        setup_db(dbname, path_to_backup)
    elif action == 'complex':
        complex(dbname)
    else:
        print usage

