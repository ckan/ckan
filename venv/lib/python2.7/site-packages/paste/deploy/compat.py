# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""Python 2<->3 compatibility module"""
import sys


def print_(template, *args, **kwargs):
    template = str(template)
    if args:
        template = template % args
    elif kwargs:
        template = template % kwargs
    sys.stdout.writelines(template)

if sys.version_info < (3, 0):
    basestring = basestring
    from ConfigParser import ConfigParser
    from urllib import unquote
    iteritems = lambda d: d.iteritems()
    dictkeys = lambda d: d.keys()

    def reraise(t, e, tb):
        exec('raise t, e, tb', dict(t=t, e=e, tb=tb))
else:
    basestring = str
    from configparser import ConfigParser
    from urllib.parse import unquote
    iteritems = lambda d: d.items()
    dictkeys = lambda d: list(d.keys())

    def reraise(t, e, tb):
        raise e.with_traceback(tb)
