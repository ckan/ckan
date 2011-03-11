#!/usr/bin/env python
usage = """
WSGI Script for CKAN
====================

Set Apache to run this WSGI Script via a symlink that is adjacent to your CKAN
config file in the file system.

Example:
  Find this script's installed path::
      $ python -c 'import ckan; print ckan.__path__'
      ['/usr/lib/pymodules/python2.6/ckan/']
  
  Create symlink::
      $ ln -s /usr/lib/pymodules/python2.6/ckan/wsgi.py /etc/ckan/dgu.py

  Apache config line::
      WSGIScriptAlias / /etc/ckan/dgu.py

  dgu.py will load the Pylons config: dgu.ini (looking in the same directory.)

"""
import os
import sys
from apachemiddleware import MaintenanceResponse

symlink_filepath = __file__
if os.path.basename(symlink_filepath) == 'wsgi.py':
    print usage
    sys.exit(1)
config_filepath = symlink_filepath.replace('.py', '.ini')
assert os.path.exists(config_filepath), 'Cannot find file %r (from symlink %r)' % (config_filepath, __file__)

# enable logging
from paste.script.util.logging_config import fileConfig
fileConfig(config_filepath)

from paste.deploy import loadapp
application = loadapp('config:%s' % config_filepath)
application = MaintenanceResponse(application)

