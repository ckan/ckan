import os
import sys
import hashlib

datapusher_home = os.environ.get('CKAN_DATAPUSHER_HOME', '/usr/lib/ckan/datapusher')
activate_this = os.path.join(datapusher_home, 'bin/activate_this.py')
execfile(activate_this, dict(__file__=activate_this))

import ckanserviceprovider.web as web
from datapusher import jobs
os.environ['JOB_CONFIG'] = '/etc/ckan/datapusher_settings.py'

web.configure()
application = web.app
