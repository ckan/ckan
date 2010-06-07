'''
Daily script for gov server
'''
import os
import logging
import sys
import zipfile
import traceback
import datetime

LOG_FILENAME = os.path.expanduser('~/gov-daily.log')
ONS_CACHE_DIR = os.path.expanduser('~/ons_data')
DUMP_DIR = os.path.expanduser('~/dump/')
# e.g. hmg.ckan.net-20091125.json.gz	
DUMP_FILE_BASE = os.path.expanduser('hmg.ckan.net-%Y-%m-%d')
TMP_FILEPATH = '/tmp/dump'
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

# Check database looks right
num_packages_before = model.Session.query(model.Package).count()
logging.info('Number of existing packages: %i' % num_packages_before)
if num_packages_before < 2500:
    logging.error('Expected more packages.')
    sys.exit(1)

# Import recent ONS data
if not os.path.exists(ONS_CACHE_DIR):
    logging.info('Creating ONS cache dir: %s' % ONS_CACHE_DIR)
    os.makedirs(ONS_CACHE_DIR)
try:
    logging.info('Importing recent ONS packages')
    new_packages, num_packages_after = ons_download.import_recent(ONS_CACHE_DIR, log=True)
except Exception, e:
    logging.error('Exception %s importing recent ONS packages: %s', str(type(e)), traceback.format_exc())
else:
    logging.info('Number of packages now: %i' % num_packages_after)

time_taken = (datetime.datetime.today() - start_time).seconds
logging.info('Time taken (so far): %i seconds' % time_taken)

# Dump
logging.info('Creating database dump')
if not os.path.exists(DUMP_DIR):
    logging.info('Creating dump dir: %s' % DUMP_DIR)
    os.makedirs(DUMP_DIR)
dump_file_base = start_time.strftime(DUMP_FILE_BASE)
csv_dump_filename_base = dump_file_base + '.csv'
json_dump_filename_base = dump_file_base + '.json'
csv_filepath = DUMP_DIR + csv_dump_filename_base + '.zip'
json_filepath = DUMP_DIR + json_dump_filename_base + '.zip'
query = model.Session.query(model.Package)
tmp_file = open(TMP_FILEPATH, 'w')
logging.info('Creating CSV file: %s' % csv_filepath)
dumper.SimpleDumper().dump_csv(tmp_file, query)
tmp_file.close()
csv_file = zipfile.ZipFile(csv_filepath, 'w')
csv_file.write(TMP_FILEPATH, dump_file_base)
csv_file.close()
tmp_file = open(TMP_FILEPATH, 'w')
logging.info('Creating JSON file: %s' % json_filepath)
dumper.SimpleDumper().dump_json(tmp_file, query)
tmp_file.close()
json_file = zipfile.ZipFile(json_filepath, 'w')
json_file.write(TMP_FILEPATH, dump_file_base)
json_file.close()
#logging.info('Transferring dumps to ckan.net')
#TODO

# Log footer
time_taken = (datetime.datetime.today() - start_time).seconds
logging.info('Time taken (total): %i seconds' % time_taken)
logging.info('----------------------------')
