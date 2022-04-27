# encoding: utf-8

# This file contains commonly used parts of external libraries. The idea is
# to help in removing helpers from being used as a dependency by many files
# but at the same time making it easy to change for example the json lib
# used.
#
# NOTE:  This file is specificaly created for
# from ckan.common import x, y, z to be allowed
from __future__ import annotations

import logging
from collections.abc import MutableMapping

from typing import (
    Any, Iterable, Optional, TYPE_CHECKING,
    TypeVar, cast, overload, Container, Union)
from typing_extensions import Literal

import flask

from werkzeug.local import Local, LocalProxy

from flask_babel import (gettext as flask_ugettext,
                         ngettext as flask_ungettext)

import simplejson as json  # type: ignore # noqa: re-export
import ckan.lib.maintain as maintain
from ckan.config.declaration import Declaration, Key

if TYPE_CHECKING:
    # starting from python 3.7 the following line can be used without any
    # conditions after `annotation` import from `__future__`
    MutableMapping = MutableMapping[str, Any]

log = logging.getLogger(__name__)


@maintain.deprecated('All web requests are served by Flask', since="2.10.0")
def is_flask_request():
    u'''
    This function is deprecated. All CKAN requests are now served by Flask
    '''
    return True


def streaming_response(data: Iterable[Any],
                       mimetype: str = u'application/octet-stream',
                       with_context: bool = False) -> flask.Response:
    iter_data = iter(data)

    if with_context:
        iter_data = flask.stream_with_context(iter_data)
    resp = flask.Response(iter_data, mimetype=mimetype)

    return resp


def ugettext(*args: Any, **kwargs: Any) -> str:
    return cast(str, flask_ugettext(*args, **kwargs))


_ = ugettext


def ungettext(*args: Any, **kwargs: Any) -> str:
    return cast(str, flask_ungettext(*args, **kwargs))


class CKANConfig(MutableMapping):
    u'''Main CKAN configuration object

    This is a dict-like object that also proxies any changes to the
    Flask and Pylons configuration objects.

    The actual `config` instance in this module is initialized in the
    `load_environment` method with the values of the ini file or env vars.

    '''
    store: dict[str, Any]

    def __init__(self, *args: Any, **kwargs: Any):
        self.store = dict()
        self.update(dict(*args, **kwargs))

    def __getitem__(self, key: str):
        return self.store[key]

    def __iter__(self):
        return iter(self.store)

    def __len__(self):
        return len(self.store)

    def __repr__(self):
        return self.store.__repr__()

    def copy(self) -> dict[str, Any]:
        return self.store.copy()

    def clear(self) -> None:
        self.store.clear()
        try:
            flask.current_app.config.clear()
        except RuntimeError:
            pass

    def __setitem__(self, key: str, value: Any):
        self.store[key] = value
        try:
            flask.current_app.config[key] = value
        except RuntimeError:
            pass

    def __delitem__(self, key: str):
        del self.store[key]
        try:
            del flask.current_app.config[key]
        except RuntimeError:
            pass

    def get_value(self, key: str) -> Any:
        if self.get("config.mode") == "strict":
            return self[key]

        option = config_declaration.get(key)
        if not option:
            log.warning("Option %s is not declared", key)
            return self.get(key)

        value = self.get(key, option.default)
        return option._normalize(value)

    def subset(
            self, pattern: Key,
            exclude: Optional[Container[Union[str, Key]]] = None
    ) -> dict[str, Any]:
        subset = {}
        exclude = exclude or set()
        for k, v in self.store.items():
            if k in exclude or pattern != k:
                continue
            subset[k] = v
        return subset


def _get_request():
    return flask.request


class CKANRequest(LocalProxy):
    u'''Common request object

    This is just a wrapper around LocalProxy so we can handle some special
    cases for backwards compatibility.
    '''

    @property
    @maintain.deprecated('Use `request.args` instead of `request.params`',
                         since="2.10.0")
    def params(self):
        '''This property is deprecated.

        Special case as Pylons' request.params is used all over the place.  All
        new code meant to be run just in Flask (eg views) should always use
        request.args

        '''
        return cast(flask.Request, self).args


def _get_c():
    return flask.g


def _get_session():
    return flask.session


def asbool(obj: Any) -> bool:
    """Convert a string (e.g. 1, true, True) into a boolean.

    Example::

        assert asbool("yes") is True

    """

    if isinstance(obj, str):
        obj = obj.strip().lower()
        if obj in truthy:
            return True
        elif obj in falsy:
            return False
        else:
            raise ValueError(u"String is not true/false: {}".format(obj))
    return bool(obj)


def asint(obj: Any) -> int:
    """Convert a string into an int.

    Example::

        assert asint("111") == 111

    """
    try:
        return int(obj)
    except (TypeError, ValueError):
        raise ValueError(u"Bad integer value: {}".format(obj))


T = TypeVar('T')
SequenceT = TypeVar('SequenceT', "list[Any]", "tuple[Any]")


@overload
def aslist(obj: str,
           sep: Optional[str] = None,
           strip: bool = True) -> list[str]:
    ...


@overload
def aslist(obj: SequenceT,
           sep: Optional[str] = None,
           strip: bool = True) -> SequenceT:
    ...


@overload
def aslist(obj: Literal[None],
           sep: Optional[str] = None,
           strip: bool = True) -> list[str]:
    ...


def aslist(obj: Any, sep: Optional[str] = None, strip: bool = True) -> Any:
    """Convert a space-separated string into a list.

    Example::

        assert aslist("a b c") == ["a", "b", "c"]

    """

    if isinstance(obj, str):
        lst = obj.split(sep)
        if strip:
            lst = [v.strip() for v in lst]
        return lst
    elif isinstance(obj, (list, tuple)):
        return cast(Any, obj)
    elif obj is None:
        return []
    else:
        return [obj]


local = Local()

# This a proxy to the bounded config object
local(u'config')

# Thread-local safe objects
config = local.config = CKANConfig()

local("config_declaration")
config_declaration = local.config_declaration = Declaration()

# Proxies to already thread-local safe objects
request = cast(flask.Request, CKANRequest(_get_request))
# Provide a `c`  alias for `g` for backwards compatibility
g: Any = LocalProxy(_get_c)
c = g
session: Any = LocalProxy(_get_session)

truthy = frozenset([u'true', u'yes', u'on', u'y', u't', u'1'])
falsy = frozenset([u'false', u'no', u'off', u'n', u'f', u'0'])
