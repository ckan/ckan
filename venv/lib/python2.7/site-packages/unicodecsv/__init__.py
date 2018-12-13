# -*- coding: utf-8 -*-
# http://semver.org/
import sys

if sys.version_info >= (3, 0):
    from unicodecsv.py3 import *
else:
    from unicodecsv.py2 import *

VERSION = (0, 14, 1)
__version__ = ".".join(map(str, VERSION))
