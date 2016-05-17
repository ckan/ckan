# This file contains commonly used parts of external libraries. The idea is
# to help in removing helpers from being used as a dependency by many files
# but at the same time making it easy to change for example the json lib
# used.
#
# NOTE:  This file is specificaly created for
# from ckan.common import x, y, z to be allowed

import flask
import pylons

from flask.ext.babel import gettext as flask_gettext
from pylons.i18n import _ as pylons_gettext, ungettext

from pylons import g, session, response
import simplejson as json

try:
    from collections import OrderedDict  # from python 2.7
except ImportError:
    from sqlalchemy.util import OrderedDict


def is_flask():
    '''
    A centralised way to determine whether to return flask versions of common
    functions, or Pylon versions.

    Currently using the presence of `flask.request`, though we may want to
    change that for something more robust.
    '''
    if flask.request:
        return True
    else:
        return False


class Request(object):
    '''
    Wraps the request object, returning attributes from either the Flask or
    Pylons request object, depending of whether flask.request is available.
    '''
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
        if '%s' in text:
            return flask_gettext(text).replace('{}', '%s')
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
