import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Make sure messages are not translated when running the tests
# (setting the environment variable here may be too late already,
# in this case you must set it manually before running the tests).
os.environ['LANGUAGE'] = 'C'

# Enable deprecation warnings (disabled by default in Python > 2.6).
import warnings
warnings.simplefilter('default')

import pkg_resources
pkg_resources.require('FormEncode')
