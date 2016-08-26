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

from flask_babel import gettext as flask_gettext
from pylons.i18n import _ as pylons_gettext, ungettext

from pylons import g, response
import simplejson as json

try:
    from collections import OrderedDict  # from python 2.7
except ImportError:
    from sqlalchemy.util import OrderedDict


def is_flask():
    u'''
    A centralised way to determine whether to return flask versions of common
    functions, or Pylon versions.

    Currently using the presence of `flask.request`, though we may want to
    change that for something more robust.
    '''
    try:
        pylons.request.environ
        pylons_request_available = True
    except TypeError:
        pylons_request_available = False

    if (flask.request and
            (flask.request.environ.get(u'ckan.app') == u'flask_app' or
             flask.request.environ.get(u'ckan.wsgiparty.setup') or
             not pylons_request_available)):
        return True
    else:
        return False


class Request(object):
    u'''
    Wraps the request object, returning attributes from either the Flask or
    Pylons request object, depending of whether flask.request is available.
    '''

    @property
    def params(self):
        u''' Special case as request.params is used all over the place.
        '''
        if is_flask():
            return flask.request.args
        else:
            return pylons.request.params

    def __getattr__(self, name):
        if is_flask():
            return getattr(flask.request, name, None)
        else:
            return getattr(pylons.request, name, None)

request = Request()


def _(text):
    # TODO: As is this will only work in the context of a web request
    # Do we need something for non-web processes like paster commands?
    # Pylons have the translator object which we need to fake but maybe
    # that's not necessary at all
    if is_flask():
        # TODO: For some reasone the Flask gettext changes 'String %s' to
        # 'String {}' (maybe it's the babel version?)
        if u'%s' in text:
            return flask_gettext(text).replace(u'{}', u'%s')
        else:
            return flask_gettext(text)
    else:
        return pylons_gettext(text)


class PylonsStyleContext(object):

    def __getattr__(self, name):
        if is_flask():
            return getattr(flask.g, name, None)
        else:
            return getattr(pylons.c, name, None)

    def __setattr__(self, name, value):
        if is_flask():
            return setattr(flask.g, name, value)
        else:
            return setattr(pylons.c, name, value)

    def __delattr__(self, name):
        if is_flask():
            return delattr(flask.g, name, None)
        else:
            return delattr(pylons.c, name, None)


c = PylonsStyleContext()


class Session():

    def __getattr__(self, name):
        if is_flask():
            return getattr(flask.session, name, None)
        else:
            return getattr(pylons.session, name, None)

    def __setattr__(self, name, value):
        if is_flask():
            return setattr(flask.session, name, value)
        else:
            return setattr(pylons.session, name, value)

    def __delattr__(self, name):
        if is_flask():
            return delattr(flask.session, name, None)
        else:
            return delattr(pylons.session, name, None)

session = Session()


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
