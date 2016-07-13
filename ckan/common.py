# encoding: utf-8

# This file contains commonly used parts of external libraries. The idea is
# to help in removing helpers from being used as a dependency by many files
# but at the same time making it easy to change for example the json lib
# used.
#
# NOTE:  This file is specificaly created for
# from ckan.common import x, y, z to be allowed

from collections import MutableMapping

import flask
import pylons

from werkzeug.local import Local

from pylons.i18n import _, ungettext
from pylons import g, c, request, session, response
import simplejson as json

try:
    from collections import OrderedDict  # from python 2.7
except ImportError:
    from sqlalchemy.util import OrderedDict


class CKANConfig(MutableMapping):
    u'''Main CKAN configuration object

    This is a dict-like object that also proxies any changes to the
    Flask and Pylons configuration objects.

    The actual `config` instance in this module is initialized in the
    `load_environment` method with the values of the ini file or env vars.

    '''

    def __init__(self, *args, **kwargs):
        self.store = dict()
        self.update(dict(*args, **kwargs))

    def __getitem__(self, key):
        return self.store[key]

    def __iter__(self):
        return iter(self.store)

    def __len__(self):
        return len(self.store)

    def __repr__(self):
        return self.store.__repr__()

    def copy(self):
        return self.store.copy()

    def clear(self):
        self.store.clear()

        try:
            flask.current_app.config.clear()
        except RuntimeError:
            pass
        try:
            pylons.config.clear()
            # Pylons set this default itself
            pylons.config[u'lang'] = None
        except TypeError:
            pass

    def __setitem__(self, key, value):
        self.store[key] = value
        try:
            flask.current_app.config[key] = value
        except RuntimeError:
            pass
        try:
            pylons.config[key] = value
        except TypeError:
            pass

    def __delitem__(self, key):
        del self.store[key]
        try:
            del flask.current_app.config[key]
        except RuntimeError:
            pass
        try:
            del pylons.config[key]
        except TypeError:
            pass

local = Local()

# This a proxy to the bounded config object
local(u'config')

# Thread-local safe objects
config = local.config = CKANConfig()
