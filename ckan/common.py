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

from werkzeug.local import Local, LocalProxy

from pylons.i18n import _, ungettext
from pylons import response
import simplejson as json

try:
    from collections import OrderedDict  # from python 2.7
except ImportError:
    from sqlalchemy.util import OrderedDict


def is_flask_request():
    u'''
    A centralized way to determine whether we are in the context of a
    request being served by Flask or Pylons
    '''
    try:
        pylons.request.environ
        pylons_request_available = True
    except TypeError:
        pylons_request_available = False

    return (flask.request and
            (flask.request.environ.get(u'ckan.app') == u'flask_app' or
             not pylons_request_available))


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


def _get_request():
    if is_flask_request():
        return flask.request
    else:
        return pylons.request


class CKANRequest(LocalProxy):
    u'''Common request object

    This is just a wrapper around LocalProxy so we can handle some special
    cases for backwards compatibility.

    LocalProxy will forward to Flask or Pylons own request objects depending
    on the output of `_get_request` (which essentially calls
    `is_flask_request`) and at the same time provide all objects methods to be
    able to interact with them transparently.
    '''

    @property
    def params(self):
        u''' Special case as Pylons' request.params is used all over the place.
        All new code meant to be run just in Flask (eg views) should always
        use request.args
        '''
        try:
            return super(CKANRequest, self).params
        except AttributeError:
            return self.args


def _get_c():
    if is_flask_request():
        return flask.g
    else:
        return pylons.c


def _get_session():
    if is_flask_request():
        return flask.session
    else:
        return pylons.session


local = Local()

# This a proxy to the bounded config object
local(u'config')

# Thread-local safe objects
config = local.config = CKANConfig()

# Proxies to already thread-local safe objects
request = CKANRequest(_get_request)
# Provide a `c`  alias for `g` for backwards compatibility
g = c = LocalProxy(_get_c)
session = LocalProxy(_get_session)
