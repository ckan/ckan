'''
Daily script for gov server
'''
import os
import logging
import sys
import zipfile
import traceback
import datetime
import re

LOG_FILENAME = os.path.expanduser('~/gov-daily.log')
DUMP_DIR = os.path.expanduser('~/dump/')
DUMP_FILE_BASE = os.path.expanduser('hmg.ckan.net-%Y-%m-%d')
TMP_FILEPATH = '/tmp/dump'
BACKUP_DIR = os.path.expanduser('~/backup/')
BACKUP_FILE_BASE = os.path.expanduser('%s.%Y-%m-%d.pg_dump')
USAGE = '''Daily script for government
Usage: python %s [config.ini]
''' % sys.argv[0]

logging.basicConfig(filename=LOG_FILENAME, level=logging.INFO)
logging.info('----------------------------')
logging.info('Starting daily script')
start_time = datetime.datetime.today()
logging.info(start_time.strftime('%H:%M %d-%m-%Y'))

if len(sys.argv) < 2 or sys.argv[1] in ('--help', '-h'):
    err = 'Error: Please specify config file.'
    print USAGE, err
    logging.error('%s\n%s' % (USAGE, err))
    sys.exit(1)
config_file = sys.argv[1]
path = os.path.abspath(config_file)
import loadconfig
loadconfig.load_config(path)

import ckan.model as model
import ckan.getdata.ons_download as ons_download
import ckan.lib.dumper as dumper
from pylons import config

def report_time_taken():
    time_taken = (datetime.datetime.today() - start_time).seconds
    logging.info('Time taken: %i seconds' % time_taken)


# Check database looks right
num_packages_before = model.Session.query(model.Package).count()
logging.info('Number of existing packages: %i' % num_packages_before)
if num_packages_before < 2500:
    logging.error('Expected more packages.')
#    sys.exit(1)

# Import recent ONS data - REMOVED

# Create dumps for users
logging.info('Creating database dump')
if not os.path.exists(DUMP_DIR):
    logging.info('Creating dump dir: %s' % DUMP_DIR)
    os.makedirs(DUMP_DIR)
query = model.Session.query(model.Package)
for file_type, dumper in (('csv', dumper.SimpleDumper().dump_csv),
                          ('json', dumper.SimpleDumper().dump_json),
                          ):
    dump_file_base = start_time.strftime(DUMP_FILE_BASE)
    dump_filename = '%s.%s' % (dump_file_base, file_type)
    dump_filepath = DUMP_DIR + dump_filename + '.zip'
    tmp_file = open(TMP_FILEPATH, 'w')
    logging.info('Creating %s file: %s' % (file_type, dump_filepath))
    dumper(tmp_file, query)
    tmp_file.close()
    dump_file = zipfile.ZipFile(dump_filepath, 'w', zipfile.ZIP_DEFLATED)
    dump_file.write(TMP_FILEPATH, dump_filename)
    dump_file.close()
report_time_taken()

# Create complete backup
def get_db_config(): # copied from fabfile
    url = config['sqlalchemy.url']
    # e.g. 'postgres://tester:pass@localhost/ckantest3'
    db_details = re.match('^\s*(?P<db_type>\w*)://(?P<db_user>\w*):(?P<db_pass>[^@]*)@(?P<db_host>[\w\.]*)/(?P<db_name>[\w.-]*)', url).groupdict()
    return db_details
db_details = get_db_config()
ckan_instance_name = config['__file__'].split('/')[-2]
pg_dump_filename = start_time.strftime(BACKUP_FILE_BASE.replace('%s', ckan_instance_name))
pg_dump_filepath = os.path.join(BACKUP_DIR, pg_dump_filename)
cmd = 'export PGPASSWORD=%s&&pg_dump -U %s -h %s %s > %s' % (db_details['db_pass'], db_details['db_user'], db_details['db_host'], db_details['db_name'], pg_dump_filepath)
logging.info('Backup command: %s' % cmd)
ret = os.system(cmd)
if ret == 0:
    logging.info('Backup successful: %s' % pg_dump_filepath)
else:
    logging.error('Backup error: %s' % ret)


# Log footer
report_time_taken()
logging.info('Finished daily script')
logging.info('----------------------------')
