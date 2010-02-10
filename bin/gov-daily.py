'''
Daily script for gov server
'''
import os
import logging
import sys
import gzip
import traceback
import datetime

LOG_FILENAME = os.path.expanduser('~/gov-daily.log')
ONS_CACHE_DIR = os.path.expanduser('~/ons_data')
DUMP_FILE_BASE = os.path.expanduser('~/data.gov.uk-daily')
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
import ckan.lib.ons_data
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
    new_packages, num_packages_after = ckan.lib.ons_data.import_recent(ONS_CACHE_DIR, log=True)
except Exception, e:
    logging.error('Exception %s importing recent ONS packages: %s', str(type(e)), traceback.format_exc())
else:
    logging.info('Number of packages now: %i' % num_packages_after)

time_taken = (datetime.datetime.today() - start_time).seconds
logging.info('Time taken (so far): %i seconds' % time_taken)

# Dump
logging.info('Creating database dump')
dump_filepath_base = DUMP_FILE_BASE
csv_filepath = dump_filepath_base + '.csv.gz'
json_filepath = dump_filepath_base + '.json.gz'
csv_file = gzip.open(csv_filepath, 'wb')
json_file = gzip.open(json_filepath, 'wb')
query = model.Session.query(model.Package)
logging.info('Creating CSV file: %s' % csv_filepath)
dumper.SimpleDumper().dump_csv(csv_file, query)
csv_file.close()
logging.info('Creating JSON file: %s' % json_filepath)
dumper.SimpleDumper().dump_json(json_file, query)
json_file.close()
#logging.info('Transferring dumps to ckan.net')
#TODO

# Log footer
time_taken = (datetime.datetime.today() - start_time).seconds
logging.info('Time taken (total): %i seconds' % time_taken)
logging.info('----------------------------')
