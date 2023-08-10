# encoding: utf-8

'''Helper functions

Consists of functions to typically be used within templates, but also
available to Controllers. This module is available to templates as 'h'.
'''
from __future__ import annotations

import email.utils
import datetime
import logging
import re
import os
import pytz
import tzlocal
import pprint
import copy
import uuid
import functools
import unicodedata

from collections import defaultdict
from typing import (
    Any, Callable, Match, NoReturn, cast, Dict,
    Iterable, Optional, TypeVar, Union)

import dominate.tags as dom_tags
from markdown import markdown
from bleach import clean as bleach_clean, ALLOWED_TAGS, ALLOWED_ATTRIBUTES
from ckan.common import asbool, config, current_user
from flask import flash
from flask import get_flashed_messages as _flask_get_flashed_messages
from flask import redirect as _flask_redirect
from flask import _request_ctx_stack
from flask import url_for as _flask_default_url_for
from werkzeug.routing import BuildError as FlaskRouteBuildError
from ckan.lib import i18n
from ckan.plugins.core import plugin_loaded

from urllib.parse import (
    urlencode, quote, unquote, urlparse, urlunparse
)

import ckan.config
import ckan.exceptions
import ckan.model as model
import ckan.lib.formatters as formatters
import ckan.lib.maintain as maintain
import ckan.lib.datapreview as datapreview
import ckan.logic as logic
import ckan.lib.uploader as uploader
import ckan.authz as authz
import ckan.plugins as p
import ckan


from ckan.lib.pagination import Page  # type: ignore # noqa: re-export
from ckan.common import _, ungettext, g, request, json

from ckan.lib.webassets_tools import include_asset, render_assets
from markupsafe import Markup, escape
from textwrap import shorten
from ckan.types import Context, Response

T = TypeVar("T")
Helper = TypeVar("Helper", bound=Callable[..., Any])

log = logging.getLogger(__name__)

MARKDOWN_TAGS = set([
    'del', 'dd', 'dl', 'dt', 'h1', 'h2',
    'h3', 'img', 'kbd', 'p', 'pre', 's',
    'sup', 'sub', 'strike', 'br', 'hr'
]).union(ALLOWED_TAGS)

MARKDOWN_ATTRIBUTES = copy.deepcopy(ALLOWED_ATTRIBUTES)
MARKDOWN_ATTRIBUTES.setdefault('img', []).extend(['src', 'alt', 'title'])

LEGACY_ROUTE_NAMES = {
    'home': 'home.index',
    'about': 'home.about',
    'search': 'dataset.search',
    'dataset_read': 'dataset.read',
    'dataset_groups': 'dataset.groups',
    'group_index': 'group.index',
    'group_about': 'group.about',
    'group_read': 'group.read',
    'organizations_index': 'organization.index',
    'organization_read': 'organization.read',
    'organization_about': 'organization.about',

    # Deprecated since v2.10
    'dataset_activity': 'activity.package_activity',
    'dataset.activity': 'activity.package_activity',
    'group_activity': 'activity.group_activity',
    'group.activity': 'activity.group_activity',
    'organization_activity': 'activity.organization_activity',
    'organization.activity': 'activity.organization_activity',
    "user.activity": "activity.user_activity",
    "dashboard.index": "activity.dashboard",
    "dataset.changes_multiple": "activity.package_changes_multiple",
    "dataset.changes": "activity.package_changes",
    "group.changes_multiple": "activity.group_changes_multiple",
    "group.changes": "activity.group_changes",
    "organization.changes_multiple": "activity.organization_changes_multiple",
    "organization.changes": "activity.organization_changes",

}


class HelperAttributeDict(Dict[str, Callable[..., Any]]):
    """Collection of CKAN native and extension-provided helpers.
    """
    def __missing__(self, key: str) -> NoReturn:
        raise ckan.exceptions.HelperError(
            'Helper \'{key}\' has not been defined.'.format(
                key=key
            )
        )

    def __getattr__(self, key: str) -> Callable[..., Any]:
        try:
            return self[key]
        except ckan.exceptions.HelperError as e:
            raise AttributeError(e)


# Builtin helper functions.
_builtin_functions: dict[str, Callable[..., Any]] = {}
helper_functions = HelperAttributeDict()


class literal(Markup):  # noqa
    """Represents an HTML literal.

    """
    __slots__ = ()

    @classmethod
    def escape(cls, s: Optional[str]) -> Markup:
        if s is None:
            return Markup(u"")
        return super(literal, cls).escape(s)


def core_helper(f: Helper, name: Optional[str] = None) -> Helper:
    """
    Register a function as a builtin helper method.
    """
    def _get_name(func_or_class: Union[Callable[..., Any], type]) -> str:
        # Handles both methods and class instances.
        try:
            return func_or_class.__name__
        except AttributeError:
            return cast(type, func_or_class.__class__).__name__

    _builtin_functions[name or _get_name(f)] = f
    return f


def _is_chained_helper(func: Callable[..., Any]) -> bool:
    return getattr(func, 'chained_helper', False)


def chained_helper(func: Helper) -> Helper:
    '''Decorator function allowing helper functions to be chained.

    This chain starts with the first chained helper to be registered and
    ends with the original helper (or a non-chained plugin override
    version). Chained helpers must accept an extra parameter,
    specifically the next helper in the chain, for example::

            helper(next_helper, *args, **kwargs).

    The chained helper function may call the next_helper function,
    optionally passing different values, handling exceptions,
    returning different values and/or raising different exceptions
    to the caller.

    Usage::

        from ckan.plugins.toolkit import chained_helper

        @chained_helper
        def ckan_version(next_func, **kw):

            return next_func(**kw)

    :param func: chained helper function
    :type func: callable

    :returns: chained helper function
    :rtype: callable

    '''
    # type_ignore_reason: custom attribute
    func.chained_helper = True  # type: ignore
    return func


def _datestamp_to_datetime(datetime_: Any) -> Optional[datetime.datetime]:
    ''' Converts a datestamp to a datetime.  If a datetime is provided it
    just gets returned.

    :param datetime_: the timestamp
    :type datetime_: string or datetime

    :rtype: datetime
    '''
    if isinstance(datetime_, str):
        try:
            datetime_ = date_str_to_datetime(datetime_)
        except TypeError:
            return None
        except ValueError:
            return None
    # check we are now a datetime
    if not isinstance(datetime_, datetime.datetime):
        return None

    if datetime_.tzinfo is not None:
        return datetime_

    # all dates are considered UTC internally,
    # change output if `ckan.display_timezone` is available
    datetime_ = datetime_.replace(tzinfo=pytz.utc)
    datetime_ = datetime_.astimezone(get_display_timezone())

    return datetime_


@core_helper
def redirect_to(*args: Any, **kw: Any) -> Response:
    '''Issue a redirect: return an HTTP response with a ``302 Moved`` header.

    This is a wrapper for :py:func:`flask.redirect` that maintains the
    user's selected language when redirecting.

    The arguments to this function identify the route to redirect to, they're
    the same arguments as :py:func:`ckan.plugins.toolkit.url_for` accepts,
    for example::

        import ckan.plugins.toolkit as toolkit

        # Redirect to /dataset/my_dataset.
        return toolkit.redirect_to('dataset.read',
                            id='my_dataset')

    Or, using a named route::

        return toolkit.redirect_to('dataset.read', id='changed')

    If given a single string as argument, this redirects without url parsing

        return toolkit.redirect_to('http://example.com')
        return toolkit.redirect_to('/dataset')
        return toolkit.redirect_to('/some/other/path')

    '''
    # Routes router doesn't like unicode args
    uargs = [str(arg) if isinstance(arg, str) else arg for arg in args]

    _url = ''
    skip_url_parsing = False
    parse_url = kw.pop('parse_url', False)
    if uargs and len(uargs) == 1 and isinstance(uargs[0], str) \
            and (uargs[0].startswith('/') or is_url(uargs[0])) \
            and parse_url is False:
        skip_url_parsing = True
        _url = uargs[0]

    if skip_url_parsing is False:
        _url = url_for(*uargs, **kw)

    if _url.startswith('/'):
        _url = str(config['ckan.site_url'].rstrip('/') + _url)

    return cast(Response, _flask_redirect(_url))


@core_helper
def get_site_protocol_and_host() -> Union[tuple[str, str], tuple[None, None]]:
    '''Return the protocol and host of the configured `ckan.site_url`.
    This is needed to generate valid, full-qualified URLs.

    If `ckan.site_url` is set like this::

        ckan.site_url = http://example.com

    Then this function would return a tuple `('http', 'example.com')`
    If the setting is missing, `(None, None)` is returned instead.

    '''
    site_url = config.get('ckan.site_url')
    if site_url is not None:
        parsed_url = urlparse(site_url)
        return (parsed_url.scheme, parsed_url.netloc)
    return (None, None)


def _get_auto_flask_context():
    '''
    Provides a Flask test request context if we are outside the context
    of a web request (tests or CLI)
    '''

    from ckan.config.middleware import _internal_test_request_context

    # This is a normal web request, there is a request context present
    if _request_ctx_stack.top:
        return None

    # We are outside a web request. A test web application was created
    # (and with it a test request context with the relevant configuration)
    if _internal_test_request_context:
        return _internal_test_request_context

    from ckan.tests.pytest_ckan.ckan_setup import _tests_test_request_context
    if _tests_test_request_context:
        return _tests_test_request_context


@core_helper
def url_for(*args: Any, **kw: Any) -> str:
    '''Return the URL for an endpoint given some parameters.

    This is a wrapper for :py:func:`flask.url_for`
    and :py:func:`routes.url_for` that adds some extra features that CKAN
    needs.

    To build a URL for a Flask view, pass the name of the blueprint and the
    view function separated by a period ``.``, plus any URL parameters::

        url_for('api.action', ver=3, logic_function='status_show')
        # Returns /api/3/action/status_show

    For a fully qualified URL pass the ``_external=True`` parameter. This
    takes the ``ckan.site_url`` and ``ckan.root_path`` settings into account::

        url_for('api.action', ver=3, logic_function='status_show',
                _external=True)
        # Returns http://example.com/api/3/action/status_show

    URLs built by Pylons use the Routes syntax::

        url_for(controller='my_ctrl', action='my_action', id='my_dataset')
        # Returns '/dataset/my_dataset'

    Or, using a named route::

        url_for('dataset.read', id='changed')
        # Returns '/dataset/changed'

    Use ``qualified=True`` for a fully qualified URL when targeting a Pylons
    endpoint.

    For backwards compatibility, an effort is made to support the Pylons syntax
    when building a Flask URL, but this support might be dropped in the future,
    so calls should be updated.
    '''
    # Get the actual string code for the locale
    locale = kw.pop('locale', None)
    if locale and isinstance(locale, i18n.Locale):
        locale = i18n.get_identifier_from_locale_class(locale)

    # remove __ckan_no_root and add after to not pollute url
    no_root = kw.pop('__ckan_no_root', False)

    # All API URLs generated should provide the version number
    if kw.get('controller') == 'api' or args and args[0].startswith('api.'):
        ver = kw.get('ver')
        if not ver:
            raise Exception('API URLs must specify the version (eg ver=3)')

    _auto_flask_context = _get_auto_flask_context()
    try:
        if _auto_flask_context:
            _auto_flask_context.push()

        # First try to build the URL with the Flask router
        # Temporary mapping for pylons to flask route names
        if len(args):
            args = (map_pylons_to_flask_route_name(args[0]),)
        my_url = _url_for_flask(*args, **kw)

    except FlaskRouteBuildError:
        raise
    finally:
        if _auto_flask_context:
            _auto_flask_context.pop()

    # Add back internal params
    kw['__ckan_no_root'] = no_root

    # Rewrite the URL to take the locale and root_path into account
    return _local_url(my_url, locale=locale, **kw)


def _url_for_flask(*args: Any, **kw: Any) -> str:
    '''Build a URL using the Flask router

    This function should not be called directly, use ``url_for`` instead

    This function tries to support the Pylons syntax for ``url_for`` and adapt
    it to the Flask one, eg::

        # Pylons
        url_for(controller='api', action='action', ver=3, qualified=True)

        # Flask
        url_for('api.action', ver=3, _external=True)


    Raises :py:exception:`werkzeug.routing.BuildError` if it couldn't
    generate a URL.
    '''
    if (len(args) and '_' in args[0]
            and '.' not in args[0]
            and not args[0].startswith('/')):
        # Try to translate Python named routes to Flask endpoints
        # eg `dataset_new` -> `dataset.new`
        args = (args[0].replace('_', '.', 1), )
    elif kw.get('controller') and kw.get('action'):
        # If `controller` and `action` are passed, build a Flask endpoint
        # from them
        # eg controller='user', action='login' -> 'user.login'
        args = ('{0}.{1}'.format(kw.pop('controller'), kw.pop('action')),)

    # Support Pylons' way of asking for full URLs

    external = kw.pop('_external', False) or kw.pop('qualified', False)

    # The API routes used to require a slash on the version number, make sure
    # we remove it
    if (args and args[0].startswith('api.') and
            isinstance(kw.get('ver'), str) and
            kw['ver'].startswith('/')):
        kw['ver'] = kw['ver'].replace('/', '')

    # Try to build the URL with flask.url_for
    try:
        my_url = _flask_default_url_for(*args, **kw)
    except FlaskRouteBuildError:
        # Check if this a relative path
        if len(args) and args[0].startswith('/'):
            my_url = args[0]
            if request.environ.get('SCRIPT_NAME'):
                my_url = request.environ['SCRIPT_NAME'] + my_url
            kw.pop('host', None)
            kw.pop('protocol', None)
            if kw:
                query_args = []
                for key, val in kw.items():
                    if isinstance(val, (list, tuple)):
                        for value in val:
                            if value is None:
                                continue
                            query_args.append(
                                u'{}={}'.format(
                                    quote(str(key)),
                                    quote(str(value))
                                )
                            )
                    else:
                        if val is None:
                            continue
                        query_args.append(
                            u'{}={}'.format(
                                quote(str(key)),
                                quote(str(val))
                            )
                        )
                if query_args:
                    my_url += '?'
                my_url += '&'.join(query_args)
        else:
            raise

    if external:
        # Don't rely on the host generated by Flask, as SERVER_NAME might not
        # be set or might be not be up to date (as in tests changing
        # `ckan.site_url`). Contrary to the Routes mapper, there is no way in
        # Flask to pass the host explicitly, so we rebuild the URL manually
        # based on `ckan.site_url`, which is essentially what we did on Pylons
        protocol, host = get_site_protocol_and_host()
        # these items cannot be empty because CKAN won't start otherwise
        assert (protocol, host) != (None, None)
        parts = urlparse(my_url)
        my_url = urlunparse((protocol, host, parts.path, parts.params,
                             parts.query, parts.fragment))

    return my_url


@core_helper
def url_for_static(*args: Any, **kw: Any) -> str:
    '''Returns the URL for static content that doesn't get translated (eg CSS)

    It'll raise CkanUrlException if called with an external URL

    This is a wrapper for :py:func:`routes.url_for`
    '''
    if args:
        url = urlparse(args[0])
        url_is_external = (url.scheme != '' or url.netloc != '')
        if url_is_external:
            raise ckan.exceptions.CkanUrlException(
                'External URL passed to url_for_static()')
    return url_for_static_or_external(*args, **kw)


@core_helper
def url_for_static_or_external(*args: Any, **kw: Any) -> str:
    '''Returns the URL for static content that doesn't get translated (eg CSS),
    or external URLs
    '''
    def fix_arg(arg: Any):
        url = urlparse(str(arg))
        url_is_relative = (url.scheme == '' and url.netloc == '' and
                           not url.path.startswith('/'))
        if url_is_relative:
            return False, '/' + url.geturl()

        return bool(url.scheme), url.geturl()

    if args:
        is_external, fixed_url = fix_arg(args[0])
        if is_external:
            return fixed_url
        args = (fixed_url, ) + args[1:]
    if kw.get('qualified', False):
        kw['protocol'], kw['host'] = get_site_protocol_and_host()
    kw['locale'] = 'default'
    return url_for(*args, **kw)


@core_helper
def is_url(*args: Any, **kw: Any) -> bool:
    '''
    Returns True if argument parses as a http, https or ftp URL
    '''
    if not args:
        return False
    try:
        url = urlparse(args[0])
    except ValueError:
        return False

    valid_schemes = config.get('ckan.valid_url_schemes')

    return url.scheme in (valid_schemes)


def _local_url(url_to_amend: str, **kw: Any):
    # If the locale keyword param is provided then the url is rewritten
    # using that locale .If return_to is provided this is used as the url
    # (as part of the language changing feature).
    # A locale of default will not add locale info to the url.

    default_locale = False
    locale = kw.pop('locale', None)
    no_root = kw.pop('__ckan_no_root', False)
    allowed_locales = ['default'] + i18n.get_locales()
    if locale and locale not in allowed_locales:
        locale = None

    _auto_flask_context = _get_auto_flask_context()

    if _auto_flask_context:
        _auto_flask_context.push()

    if locale:
        if locale == 'default':
            default_locale = True
    else:
        try:
            locale = request.environ.get('CKAN_LANG')
            default_locale = request.environ.get('CKAN_LANG_IS_DEFAULT', True)
        except TypeError:
            default_locale = True

    root = ''
    if kw.get('qualified', False) or kw.get('_external', False):
        # if qualified is given we want the full url ie http://...
        protocol, host = get_site_protocol_and_host()

        parts = urlparse(
            _flask_default_url_for('home.index', _external=True)
        )

        path = parts.path.rstrip('/')
        root = urlunparse(
            (protocol, host, path,
                parts.params, parts.query, parts.fragment))

    if _auto_flask_context:
        _auto_flask_context.pop()

    # ckan.root_path is defined when we have none standard language
    # position in the url
    root_path = config.get('ckan.root_path')
    if root_path:
        # FIXME this can be written better once the merge
        # into the ecportal core is done - Toby
        # we have a special root specified so use that
        if default_locale:
            root_path = re.sub('/{{LANG}}', '', root_path)
        else:
            root_path = re.sub('{{LANG}}', str(locale), root_path)
        # make sure we don't have a trailing / on the root
        if root_path[-1] == '/':
            root_path = root_path[:-1]
    else:
        if default_locale:
            root_path = ''
        else:
            root_path = '/' + str(locale)

    url_path = url_to_amend[len(root):]
    url = '%s%s%s' % (root, root_path, url_path)

    # stop the root being added twice in redirects
    if no_root and url_to_amend.startswith(root):
        url = url_to_amend[len(root):]
        if not default_locale:
            url = '/%s%s' % (locale, url)

    if url == '/packages':
        error = 'There is a broken url being created %s' % kw
        raise ckan.exceptions.CkanUrlException(error)

    return url


@core_helper
def url_is_local(url: str) -> bool:
    '''Returns True if url is local'''
    if not url or url.startswith('//'):
        return False
    parsed = urlparse(url)
    if parsed.scheme:
        domain = urlparse(url_for('/', qualified=True)).netloc
        if domain != parsed.netloc:
            return False
    return True


@core_helper
def full_current_url() -> str:
    ''' Returns the fully qualified current url (eg http://...) useful
    for sharing etc '''
    return (url_for(request.environ['CKAN_CURRENT_URL'], qualified=True))


@core_helper
def current_url() -> str:
    ''' Returns current url unquoted'''
    return request.environ['CKAN_CURRENT_URL']


@core_helper
def lang() -> Optional[str]:
    ''' Return the language code for the current locale eg `en` '''
    return request.environ.get('CKAN_LANG')


@core_helper
def strxfrm(s: str) -> str:
    '''
    Transform a string to one that can be used in locale-aware comparisons.
    Override this helper if you have different text sorting needs.
    '''
    return unicodedata.normalize('NFD', s).lower()


@core_helper
def ckan_version() -> str:
    '''Return CKAN version'''
    return ckan.__version__


@core_helper
def lang_native_name(lang_: Optional[str] = None) -> Optional[str]:
    ''' Return the language name currently used in it's localised form
        either from parameter or current environ setting'''
    name = lang_ or lang()
    if not name:
        return None
    locale = i18n.get_locales_dict().get(name)
    if locale:
        return locale.display_name or locale.english_name
    return name


@core_helper
def is_rtl_language() -> bool:
    return lang() in config.get('ckan.i18n.rtl_languages')


@core_helper
def get_rtl_theme() -> str:
    return config.get('ckan.i18n.rtl_theme')


@core_helper
def flash_notice(message: Any, allow_html: bool = False) -> None:
    ''' Show a flash message of type notice '''
    if allow_html:
        message = Markup(message)
    else:
        message = escape(message)
    flash(message, category='alert-info')


@core_helper
def flash_error(message: Any, allow_html: bool = False) -> None:
    ''' Show a flash message of type error '''
    if allow_html:
        message = Markup(message)
    else:
        message = escape(message)
    flash(message, category='alert-danger')


@core_helper
def flash_success(message: Any, allow_html: bool = False) -> None:
    ''' Show a flash message of type success '''
    if allow_html:
        message = Markup(message)
    else:
        message = escape(message)
    flash(message, category='alert-success')


@core_helper
def get_flashed_messages(**kwargs: Any):
    '''Call Flask's built in get_flashed_messages'''
    return _flask_get_flashed_messages(**kwargs)


def _link_active(kwargs: Any) -> bool:
    ''' creates classes for the link_to calls '''
    blueprint, endpoint = p.toolkit.get_endpoint()

    highlight_controllers = kwargs.get('highlight_controllers', [])
    if highlight_controllers and blueprint in highlight_controllers:
        return True

    return (kwargs.get('controller') == blueprint and
            kwargs.get('action') == endpoint)


def _link_to(text: str, *args: Any, **kwargs: Any) -> Markup:
    '''Common link making code for several helper functions'''
    assert len(args) < 2, 'Too many unnamed arguments'

    def _link_class(kwargs: dict[str, Any]):
        ''' creates classes for the link_to calls '''
        suppress_active_class = kwargs.pop('suppress_active_class', False)
        if not suppress_active_class and _link_active(kwargs):
            active = ' active'
        else:
            active = ''
        return kwargs.pop('class_', '') + active or None

    def _create_link_text(text: str, **kwargs: Any):
        ''' Update link text to add a icon or span if specified in the
        kwargs '''
        if kwargs.pop('inner_span', None):
            text = literal('<span>') + text + literal('</span>')
        if icon:
            text = literal('<i class="fa fa-%s"></i> ' % icon) + text
        return text

    icon = kwargs.pop('icon', None)
    cls = _link_class(kwargs)
    title = kwargs.pop('title', kwargs.pop('title_', None))
    return link_to(
        _create_link_text(text, **kwargs),
        url_for(*args, **kwargs),
        cls=cls,
        title=title
    )


def _preprocess_dom_attrs(attrs: dict[str, Any]) -> dict[str, Any]:
    """Strip leading underscore from keys of dict.

    This hack was used in `webhelpers` library for some attributes,
    like `class` that cannot be used because it special meaning in
    Python.
    """
    return {
        key.rstrip('_'): value
        for key, value in attrs.items()
        if value is not None
    }


@core_helper
def link_to(label: str, url: str, **attrs: Any) -> Markup:
    attrs = _preprocess_dom_attrs(attrs)
    attrs['href'] = url
    if label == '' or label is None:
        label = url
    return literal(str(dom_tags.a(label, **attrs)))


@core_helper
def nav_link(text: str, *args: Any, **kwargs: Any) -> Union[Markup, str]:
    '''
    :param class_: pass extra class(es) to add to the ``<a>`` tag
    :param icon: name of ckan icon to use within the link
    :param condition: if ``False`` then no link is returned

    '''
    if len(args) > 1:
        raise Exception('Too many unnamed parameters supplied')
    blueprint, endpoint = p.toolkit.get_endpoint()
    if args:
        kwargs['controller'] = blueprint or None
        kwargs['action'] = endpoint or None
    named_route = kwargs.pop('named_route', '')
    if kwargs.pop('condition', True):
        if named_route:
            link = _link_to(text, named_route, **kwargs)
        else:
            link = _link_to(text, **kwargs)
    else:
        link = ''
    return link


@core_helper
def build_nav_main(
    *args: Union[tuple[str, str], tuple[str, str, list[str]],
                 tuple[str, str, list[str], str], ]
) -> Markup:

    """Build a set of menu items.

    Outputs ``<li><a href="...">title</a></li>``

    :param args: tuples of (menu type, title) eg ('login', _('Login')).
        Third item specifies controllers which should be used to
        mark link as active.
        Fourth item specifies auth function to check permissions against.
    :type args: tuple[str, str, Optional[list], Optional[str]]

    :rtype: str
    """
    output: Markup = literal('')
    for item in args:
        padding: Any = (None,) * 4
        menu_item, title, highlight_controllers, auth_function = (
            item + padding)[:4]
        if auth_function and not check_access(auth_function):
            continue
        output += _make_menu_item(menu_item, title,
                                  highlight_controllers=highlight_controllers)
    return output


@core_helper
def build_nav_icon(menu_item: str, title: str, **kw: Any) -> Markup:
    '''Build a navigation item used for example in ``user/read_base.html``.

    Outputs ``<li><a href="..."><i class="icon.."></i> title</a></li>``.

    :param menu_item: the name of the defined menu item defined in
      config/routing as the named route of the same name
    :type menu_item: string
    :param title: text used for the link
    :type title: string
    :param kw: additional keywords needed for creating url eg ``id=...``

    :rtype: HTML literal

    '''
    return _make_menu_item(menu_item, title, **kw)


@core_helper
def build_nav(menu_item: str, title: str, **kw: Any) -> Markup:
    '''Build a navigation item used for example breadcrumbs.

    Outputs ``<li><a href="...">title</a></li>``.

    :param menu_item: the name of the defined menu item defined in
      config/routing as the named route of the same name
    :type menu_item: string
    :param title: text used for the link
    :type title: string
    :param  kw: additional keywords needed for creating url eg ``id=...``

    :rtype: HTML literal

    '''
    return _make_menu_item(menu_item, title, icon=None, **kw)


def map_pylons_to_flask_route_name(menu_item: str):
    '''returns flask routes for old fashioned route names'''
    # Pylons to Flask legacy route names mappings
    mappings = config.get('ckan.legacy_route_mappings')
    if mappings:
        if isinstance(mappings, str):
            LEGACY_ROUTE_NAMES.update(json.loads(mappings))
        elif isinstance(mappings, dict):
            LEGACY_ROUTE_NAMES.update(mappings)

    if menu_item in LEGACY_ROUTE_NAMES:
        log.info('Route name "{}" is deprecated and will be removed. '
                 'Please update calls to use "{}" instead'
                 .format(menu_item, LEGACY_ROUTE_NAMES[menu_item]))
    return LEGACY_ROUTE_NAMES.get(menu_item, menu_item)


@core_helper
def build_extra_admin_nav() -> Markup:
    '''Build extra navigation items used in ``admin/base.html`` for values
    defined in the config option ``ckan.admin_tabs``. Typically this is
    populated by extensions.

    :rtype: HTML literal

    '''
    admin_tabs_dict = config.get('ckan.admin_tabs')
    output: Markup = literal('')
    if admin_tabs_dict:
        for k, v in admin_tabs_dict.items():
            if v['icon']:
                output += build_nav_icon(k, v['label'], icon=v['icon'])
            else:
                output += build_nav(k, v['label'])
    return output


def _make_menu_item(menu_item: str, title: str, **kw: Any) -> Markup:
    ''' build a navigation item used for example breadcrumbs

    outputs <li><a href="..."></i> title</a></li>

    :param menu_item: the name of the defined menu item defined in
    config/routing as the named route of the same name
    :type menu_item: string
    :param title: text used for the link
    :type title: string
    :param **kw: additional keywords needed for creating url eg id=...

    :rtype: HTML literal

    This function is called by wrapper functions.
    '''
    controller, action = menu_item.split('.')
    item = {
        'action': action,
        'controller': controller
    }
    item.update(kw)
    active = _link_active(item)
    # Remove highlight controllers so that they won't appear in generated urls.
    item.pop('highlight_controllers', False)

    link = _link_to(title, menu_item, suppress_active_class=True, **item)
    if active:
        return literal('<li class="active">') + link + literal('</li>')
    return literal('<li>') + link + literal('</li>')


@core_helper
def default_group_type(type_: str) -> str:
    """Get default group/organization type for using site-wide.
    """
    return config.get(f'ckan.default.{type_}_type')


@core_helper
def default_package_type() -> str:
    """Get default package type for using site-wide.
    """
    return config.get('ckan.default.package_type')


def _humanize_activity(object_type: str, activity_type: str) -> str:
    """ Humanize activity types for custom objects

        Example::

          >>> _humanize_activity('Custom user', 'new_user')
          'New custom user'
          >>> _humanize_activity('dataset', 'changed_package')
          'Changed dataset'

    """
    res = activity_type.replace('_', ' ').lower()
    for obj in ['package', 'user', 'group', 'organization']:
        res = res.replace(obj, object_type)
    return res.capitalize()


@core_helper
def humanize_entity_type(entity_type: str, object_type: str,
                         purpose: str) -> Optional[str]:
    """Convert machine-readable representation of package/group type into
    human-readable form.

    Returns capitalized `entity_type` with all underscores converted
    into spaces.

    Example::

      >>> humanize_entity_type('group', 'custom_group', 'add link')
      'Add Custom Group'
      >>> humanize_entity_type('group', 'custom_group', 'breadcrumb')
      'Custom Groups'
      >>> humanize_entity_type('group', 'custom_group', 'not real purpuse')
      'Custom Group'

    Possible purposes(depends on `entity_type` and change over time)::

        `add link`: "Add [object]" button on search pages
        `breadcrumb`: "Home / [object]s / New" section in breadcrums
        `content tab`: "[object]s | Groups | Activity" tab on details page
        `create label`: "Home / ... / Create [object]" part of breadcrumb
        `create title`: "Create [object] - CKAN" section of page title
        `delete confirmation`: Confirmation popup when object is deleted
        `description placeholder`: Placeholder for description field on form
        `edit label`: "Edit [object]" label/breadcrumb/title
        `facet label`: "[object]s" label in sidebar(facets/follower counters)
        `form label`: "[object] Form" heading on object form page
        `main nav`: "[object]s" link in the header
        `view label`: "View [object]s" button on edit form
        `my label`: "My [object]s" tab in dashboard
        `name placeholder`: "<[object]>" section of URL preview on object form
        `no any objects`: No objects created yet
        `no associated label`: no gorups for dataset
        `no description`: object has no description
        `no label`: package with no organization
        `page title`: "Title - [objec]s - CKAN" section of page title
        `save label`: "Save [object]" button
        `search placeholder`: "Search [object]s..." placeholder
        `update label`: "Update [object]" button
        `you not member`: Dashboard with no groups

    """
    if entity_type == object_type:
        return None  # use the default text included in template

    if (entity_type, object_type) == ("package", "dataset"):
        # special case for the previous condition
        return

    if entity_type == "activity":
        return _humanize_activity(object_type, activity_type=purpose)

    log.debug(
        u'Humanize %s of type %s for %s', entity_type, object_type, purpose)
    templates = {
        u'add link': _(u"Add {object_type}"),
        u'breadcrumb': _(u"{object_type}s"),
        u'content tab': _(u"{object_type}s"),
        u'create label': _(u"Create {object_type}"),
        u'create title': _(u"Create {object_type}"),
        u'delete confirmation': _(
            u'Are you sure you want to delete this {object_type}?'),
        u'description placeholder': _(
            u"A little information about my {object_type}..."),
        u'edit label': _(u"Edit {object_type}"),
        u'facet label': _(u"{object_type}s"),
        u'form label': _(u"{object_type} Form"),
        u'main nav': _(u"{object_type}s"),
        u'my label': _(u"My {object_type}s"),
        u'view label': _("View {object_type}"),
        u'name placeholder': _(u"My {object_type}"),
        u'no any objects': _(
            u"There are currently no {object_type}s for this site"),
        u'no associated label': _(
            u'There are no {object_type}s associated with this dataset'),
        u'no description': _(
            u'There is no description for this {object_type}'),
        u'no label': _(u"No {object_type}"),
        u'page title': _(u"{object_type}s"),
        u'save label': _(u"Save {object_type}"),
        u'search placeholder': _(u'Search {object_type}s...'),
        u'you not member': _(u'You are not a member of any {object_type}s.'),
        u'update label': _(u"Update {object_type}"),
    }

    type_label = object_type.replace(u"_", u" ").capitalize()
    if purpose not in templates:
        return type_label

    return templates[purpose].format(object_type=type_label)


@core_helper
def get_facet_items_dict(
        facet: str,
        search_facets: Union[dict[str, dict[str, Any]], Any] = None,
        limit: Optional[int] = None,
        exclude_active: bool = False) -> list[dict[str, Any]]:
    '''Return the list of unselected facet items for the given facet, sorted
    by count.

    Returns the list of unselected facet contraints or facet items (e.g. tag
    names like "russian" or "tolstoy") for the given search facet (e.g.
    "tags"), sorted by facet item count (i.e. the number of search results that
    match each facet item).

    Reads the complete list of facet items for the given facet from
    search_facets, and filters out the facet items that the user has already
    selected.

    Arguments:
    facet -- the name of the facet to filter.
    search_facets -- dict with search facets
    limit -- the max. number of facet items to return.
    exclude_active -- only return unselected facets.

    '''
    if not search_facets \
       or not isinstance(search_facets, dict) \
       or not search_facets.get(facet, {}).get('items'):
        return []
    facets = []
    for facet_item in search_facets[facet]['items']:
        if not len(facet_item['name'].strip()):
            continue
        params_items = request.args.items(multi=True)
        if not (facet, facet_item['name']) in params_items:
            facets.append(dict(active=False, **facet_item))
        elif not exclude_active:
            facets.append(dict(active=True, **facet_item))
    # Sort descendingly by count and ascendingly by case-sensitive display name
    sort_facets: Callable[[Any], tuple[int, str]] = lambda it: (
        -it['count'], it['display_name'].lower())
    facets.sort(key=sort_facets)
    if hasattr(g, 'search_facets_limits'):
        if g.search_facets_limits and limit is None:
            limit = g.search_facets_limits.get(facet)
    # zero treated as infinite for hysterical raisins
    if limit is not None and limit > 0:
        return facets[:limit]
    return facets


@core_helper
def has_more_facets(facet: str,
                    search_facets: dict[str, dict[str, Any]],
                    limit: Optional[int] = None,
                    exclude_active: bool = False) -> bool:
    '''
    Returns True if there are more facet items for the given facet than the
    limit.

    Reads the complete list of facet items for the given facet from
    search_facets, and filters out the facet items that the user has already
    selected.

    Arguments:
    facet -- the name of the facet to filter.
    search_facets -- dict with search facets
    limit -- the max. number of facet items.
    exclude_active -- only return unselected facets.

    '''
    facets = []
    for facet_item in search_facets[facet]['items']:
        if not len(facet_item['name'].strip()):
            continue
        params_items = request.args.items(multi=True)
        if not (facet, facet_item['name']) in params_items:
            facets.append(dict(active=False, **facet_item))
        elif not exclude_active:
            facets.append(dict(active=True, **facet_item))
    if getattr(g, 'search_facets_limits', None) and limit is None:
        limit = g.search_facets_limits.get(facet)
    if limit is not None and len(facets) > limit:
        return True
    return False


@core_helper
def get_param_int(name: str, default: int = 10) -> int:
    try:
        return int(request.args.get(name, default))
    except ValueError:
        return default


def _url_with_params(url: str, params: Optional[Iterable[tuple[str,
                                                               Any]]]) -> str:
    if not params:
        return url
    params = [(k, v.encode('utf-8') if isinstance(v, str) else str(v))
              for k, v in params]
    return url + u'?' + urlencode(params)


@core_helper
def sorted_extras(package_extras: list[dict[str, Any]],
                  auto_clean: bool = False,
                  subs: Optional[dict[str, str]] = None,
                  exclude: Optional[list[str]] = None
                  ) -> list[tuple[str, Any]]:
    ''' Used for outputting package extras

    :param package_extras: the package extras
    :type package_extras: dict
    :param auto_clean: If true capitalize and replace -_ with spaces
    :type auto_clean: bool
    :param subs: substitutes to use instead of given keys
    :type subs: dict {'key': 'replacement'}
    :param exclude: keys to exclude
    :type exclude: list of strings
    '''

    # If exclude is not supplied use values defined in the config
    if not exclude:
        exclude = config.get('package_hide_extras')
    output = []
    for extra in sorted(package_extras, key=lambda x: x['key']):
        if extra.get('state') == 'deleted':
            continue
        k, v = extra['key'], extra['value']
        if k in exclude:
            continue
        if subs and k in subs:
            k = subs[k]
        elif auto_clean:
            k = k.replace('_', ' ').replace('-', ' ').title()
        if isinstance(v, (list, tuple)):
            v = ", ".join(map(str, v))
        output.append((k, v))
    return output


@core_helper
def check_access(
        action: str, data_dict: Optional[dict[str, Any]] = None) -> bool:
    context = cast(Context, {
        'model': model,
        'user': current_user.name})
    if not data_dict:
        data_dict = {}
    try:
        logic.check_access(action, context, data_dict)
        authorized = True
    except logic.NotAuthorized:
        authorized = False

    return authorized


@core_helper
def linked_user(user: Union[str, model.User],
                maxlength: int = 0,
                avatar: int = 20) -> Union[Markup, str, None]:
    if not isinstance(user, model.User):
        user_name = str(user)
        user_obj = model.User.get(user_name)
        if not user_obj:
            return user_name
        user = user_obj
    if user:
        name = user.name if model.User.VALID_NAME.match(user.name) else user.id
        displayname = user.display_name

        if maxlength and len(user.display_name) > maxlength:
            displayname = displayname[:maxlength] + '...'

        return literal(u'{icon} {link}'.format(
            icon=user_image(
                user.id,
                size=avatar
            ),
            link=link_to(
                displayname,
                url_for('user.read', id=name)
            )
        ))
    return None


@core_helper
def group_name_to_title(name: str) -> str:
    group = model.Group.by_name(name)
    if group is not None:
        return group.display_name
    return name


@core_helper
@maintain.deprecated("helpers.truncate() is deprecated and will be removed "
                     "in a future version of CKAN. Instead, please use the "
                     "builtin jinja filter instead.",
                     since="2.10.0")
def truncate(text: str,
             length: int = 30,
             indicator: str = '...',
             whole_word: bool = False) -> str:
    """Truncate ``text`` with replacement characters.

    ``length``
        The maximum length of ``text`` before replacement
    ``indicator``
        If ``text`` exceeds the ``length``, this string will replace
        the end of the string
    ``whole_word``
        If true, shorten the string further to avoid breaking a word in the
        middle.  A word is defined as any string not containing whitespace.
        If the entire text before the break is a single word, it will have to
        be broken.

    Example::

        >>> truncate('Once upon a time in a world far far away', 14)
        'Once upon a...'

    Deprecated: please use jinja filter `truncate` instead
    """
    if not text:
        return ""
    if len(text) <= length:
        return text
    short_length = length - len(indicator)
    if not whole_word:
        return text[:short_length] + indicator
    # Go back to end of previous word.
    i = short_length
    while i >= 0 and not text[i].isspace():
        i -= 1
    while i >= 0 and text[i].isspace():
        i -= 1
    if i <= 0:
        # Entire text before break is one word, or we miscalculated.
        return text[:short_length] + indicator
    return text[:i + 1] + indicator


@core_helper
def markdown_extract(text: str,
                     extract_length: int = 190) -> Union[str, Markup]:
    ''' return the plain text representation of markdown encoded text.  That
    is the texted without any html tags.  If extract_length is 0 then it
    will not be truncated.'''
    if not text:
        return ''
    plain = RE_MD_HTML_TAGS.sub('', markdown(text))
    if not extract_length or len(plain) < extract_length:
        return literal(plain)
    return literal(
        str(
            shorten(
                plain,
                width=extract_length,
                placeholder='...'
            )
        )
    )


@core_helper
def dict_list_reduce(list_: list[dict[str, T]],
                     key: str,
                     unique: bool = True) -> list[T]:
    ''' Take a list of dicts and create a new one containing just the
    values for the key with unique values if requested. '''
    new_list = []
    for item in list_:
        value = item.get(key)
        if not value or (unique and value in new_list):
            continue
        new_list.append(value)
    return new_list


_VALID_GRAVATAR_DEFAULTS = ['404', 'mm', 'identicon', 'monsterid',
                            'wavatar', 'retro']


@core_helper
def gravatar(email_hash: str,
             size: int = 100,
             default: Optional[str] = None) -> Markup:
    if default is None:
        default = config.get('ckan.gravatar_default')
    assert default is not None

    if default not in _VALID_GRAVATAR_DEFAULTS:
        # treat the default as a url
        default = quote(default, safe='')

    return literal('''<img src="//gravatar.com/avatar/%s?s=%d&amp;d=%s"
        class="user-image" width="%s" height="%s" alt="Gravatar" />'''
                   % (email_hash, size, default, size, size)
                   )


_PLAUSIBLE_HOST_IDNA = re.compile(r'^[-\w.:\[\]]*$')


@core_helper
def sanitize_url(url: str):
    '''
    Return a sanitized version of a user-provided url for use in an
    <a href> or <img src> attribute, e.g.:

    <a href="{{ h.sanitize_url(user_link) }}">

    Sanitizing urls is tricky. This is a best-effort to produce something
    valid from the sort of text users might paste into a web form, not
    intended to cover all possible valid edge-case urls.

    On parsing errors an empty string will be returned.
    '''
    try:
        parsed_url = urlparse(url)
        netloc = parsed_url.netloc.encode('idna').decode('ascii')
        if not _PLAUSIBLE_HOST_IDNA.match(netloc):
            return ''
        # quote with allowed characters from
        # https://www.ietf.org/rfc/rfc3986.txt
        parsed_url = parsed_url._replace(
            scheme=quote(unquote(parsed_url.scheme), '+'),
            path=quote(unquote(parsed_url.path), "/"),
            query=quote(unquote(parsed_url.query), "?/&="),
            params=quote(unquote(parsed_url.params), "?/&="),
            fragment=quote(unquote(parsed_url.fragment), "?/&="),
        )
        return urlunparse(parsed_url)
    except ValueError:
        return ''


@core_helper
def user_image(user_id: str, size: int = 100) -> Union[Markup, str]:
    try:
        user_dict = logic.get_action('user_show')(
            {'ignore_auth': True},
            {'id': user_id}
        )
    except logic.NotFound:
        return ''

    gravatar_default = config.get('ckan.gravatar_default')

    if user_dict['image_display_url']:
        return literal('''<img src="{url}"
                       class="user-image"
                       width="{size}" height="{size}" alt="{alt}" />'''.format(
            url=sanitize_url(user_dict['image_display_url']),
            size=size,
            alt=user_dict['name']
        ))
    elif gravatar_default == 'disabled':
        return snippet(
            'user/snippets/placeholder.html',
            size=size, user_name=user_dict['display_name'])
    else:
        return gravatar(user_dict['email_hash'], size, gravatar_default)


@core_helper
def pager_url(page: int, partial: Optional[str] = None, **kwargs: Any) -> str:
    pargs = []
    pargs.append(request.endpoint)
    kwargs['page'] = page
    return url_for(*pargs, **kwargs)


@core_helper
def get_page_number(
        params: dict[str, Any], key: str = 'page', default: int = 1) -> int:
    '''
    Return the page number from the provided params after verifying that it is
    an positive integer.

    If it fails it will abort the request with a 400 error.
    '''
    p = params.get(key, default)

    try:
        p = int(p)
        if p < 1:
            raise ValueError("Negative number not allowed")
    except ValueError:
        import ckan.lib.base as base
        base.abort(400, ('"{key}" parameter must be a positive integer'
                   .format(key=key)))

    return p


@core_helper
def get_display_timezone() -> datetime.tzinfo:
    ''' Returns a pytz timezone for the display_timezone setting in the
    configuration file or UTC if not specified.
    :rtype: timezone
    '''
    timezone_name = config.get('ckan.display_timezone')

    if timezone_name == 'server':
        return tzlocal.get_localzone()

    return pytz.timezone(timezone_name)


@core_helper
def render_datetime(datetime_: Optional[datetime.datetime],
                    date_format: Optional[str] = None,
                    with_hours: bool = False,
                    with_seconds: bool = False) -> str:
    '''Render a datetime object or timestamp string as a localised date or
    in the requested format.
    If timestamp is badly formatted, then a blank string is returned.

    :param datetime_: the date
    :type datetime_: datetime or ISO string format
    :param date_format: a date format
    :type date_format: string
    :param with_hours: should the `hours:mins` be shown
    :type with_hours: bool
    :param with_seconds: should the `hours:mins:seconds` be shown
    :type with_seconds: bool

    :rtype: string
    '''
    datetime_ = _datestamp_to_datetime(datetime_)
    if not datetime_:
        return ''

    # if date_format was supplied we use it
    if date_format:

        # See http://bugs.python.org/issue1777412
        if datetime_.year < 1900:
            year = str(datetime_.year)

            date_format = re.sub('(?<!%)((%%)*)%y',
                                 r'\g<1>{year}'.format(year=year[-2:]),
                                 date_format)
            date_format = re.sub('(?<!%)((%%)*)%Y',
                                 r'\g<1>{year}'.format(year=year),
                                 date_format)

            datetime_ = datetime.datetime(2016, datetime_.month, datetime_.day,
                                          datetime_.hour, datetime_.minute,
                                          datetime_.second)

            return datetime_.strftime(date_format)

        return datetime_.strftime(date_format)
    # the localised date
    return formatters.localised_nice_date(datetime_, show_date=True,
                                          with_hours=with_hours,
                                          with_seconds=with_seconds)


@core_helper
def date_str_to_datetime(date_str: str) -> datetime.datetime:
    '''Convert ISO-like formatted datestring to datetime object.

    This function converts ISO format date- and datetime-strings into
    datetime objects.  Times may be specified down to the microsecond.  UTC
    offset or timezone information may **not** be included in the string.

    Note - Although originally documented as parsing ISO date(-times), this
           function doesn't fully adhere to the format.  This function will
           throw a ValueError if the string contains UTC offset information.
           So in that sense, it is less liberal than ISO format.  On the
           other hand, it is more liberal of the accepted delimiters between
           the values in the string.  Also, it allows microsecond precision,
           despite that not being part of the ISO format.
    '''

    time_tuple: list[Any] = re.split(r'[^\d]+', date_str, maxsplit=5)

    # Extract seconds and microseconds
    if len(time_tuple) >= 6:
        m = re.match(r'(?P<seconds>\d{2})(\.(?P<microseconds>\d+))?$',
                     time_tuple[5])
        if not m:
            raise ValueError('Unable to parse %s as seconds.microseconds' %
                             time_tuple[5])
        seconds = int(m.groupdict('0')['seconds'])
        microseconds = int((str(m.groupdict('0')['microseconds']) +
                            '00000')[0:6])
        time_tuple = time_tuple[:5] + [seconds, microseconds]

    return datetime.datetime(
        # type_ignore_reason: typchecker can't guess number of arguments
        *list(int(item) for item in time_tuple)  # type: ignore
    )


@core_helper
def parse_rfc_2822_date(date_str: str,
                        assume_utc: bool = True
                        ) -> Optional[datetime.datetime]:
    '''Parse a date string of the form specified in RFC 2822, and return a
    datetime.

    RFC 2822 is the date format used in HTTP headers.  It should contain
    timezone information, but that cannot be relied upon.

    If date_str doesn't contain timezone information, then the 'assume_utc'
    flag determines whether we assume this string is local (with respect to the
    server running this code), or UTC.  In practice, what this means is that if
    assume_utc is True, then the returned datetime is 'aware', with an
    associated tzinfo of offset zero.  Otherwise, the returned datetime is
    'naive'.

    If timezone information is available in date_str, then the returned
    datetime is 'aware', ie - it has an associated tz_info object.

    Returns None if the string cannot be parsed as a valid datetime.

    Note: in Python3, `email.utils` always assume UTC if there is no
    timezone, so `assume_utc` has no sense in this version.

    '''
    time_tuple = email.utils.parsedate_tz(date_str)

    # Not parsable
    if not time_tuple:
        return None

    # No timezone information available in the string
    if time_tuple[-1] is None and not assume_utc:
        return datetime.datetime.fromtimestamp(
            email.utils.mktime_tz(time_tuple))
    else:
        offset = time_tuple[-1]
        if offset is None:
            offset = 0
        tz_info = _RFC2282TzInfo(offset)
    return datetime.datetime(
        *time_tuple[:6], microsecond=0, tzinfo=tz_info)


class _RFC2282TzInfo(datetime.tzinfo):
    '''
    A datetime.tzinfo implementation used by parse_rfc_2822_date() function.

    In order to return timezone information, a concrete implementation of
    datetime.tzinfo is required.  This class represents tzinfo that knows
    about it's offset from UTC, has no knowledge of daylight savings time, and
    no knowledge of the timezone name.

    '''

    def __init__(self, offset: int):
        '''
        offset from UTC in seconds.
        '''
        self.offset = datetime.timedelta(seconds=offset)

    def utcoffset(self, dt: Any):
        return self.offset

    def dst(self, dt: Any):
        '''
        Dates parsed from an RFC 2822 string conflate timezone and dst, and so
        it's not possible to determine whether we're in DST or not, hence
        returning None.
        '''
        return None

    def tzname(self, dt: Any):
        return None


@core_helper
def time_ago_from_timestamp(timestamp: int) -> str:
    ''' Returns a string like `5 months ago` for a datetime relative to now
    :param timestamp: the timestamp or datetime
    :type timestamp: string or datetime

    :rtype: string
    '''
    datetime_ = _datestamp_to_datetime(timestamp)
    if not datetime_:
        return _('Unknown')

    # the localised date
    return formatters.localised_nice_date(datetime_, show_date=False)


@core_helper
def dataset_display_name(
        package_or_package_dict: Union[dict[str, Any], model.Package]) -> str:

    if isinstance(package_or_package_dict, dict):
        return get_translated(package_or_package_dict, 'title') or \
            package_or_package_dict['name']
    else:
        # FIXME: we probably shouldn't use the same functions for
        # package dicts and real package objects
        return package_or_package_dict.title or package_or_package_dict.name


@core_helper
def dataset_link(
        package_or_package_dict: Union[dict[str, Any], model.Package]
) -> Markup:
    if isinstance(package_or_package_dict, dict):
        name = package_or_package_dict['name']
        type_ = package_or_package_dict.get('type', 'dataset')
    else:
        name = package_or_package_dict.name
        type_ = package_or_package_dict.type
    text = dataset_display_name(package_or_package_dict)
    return link_to(
        text,
        url_for('{}.read'.format(type_), id=name)
    )


@core_helper
def resource_display_name(resource_dict: dict[str, Any]) -> str:
    # TODO: (?) support resource objects as well
    name = get_translated(resource_dict, 'name')
    description = get_translated(resource_dict, 'description')
    if name:
        return name
    elif description:
        description = description.split('.')[0]
        max_len = 60
        if len(description) > max_len:
            description = description[:max_len] + '...'
        return description
    else:
        return _("Unnamed resource")


@core_helper
def resource_link(resource_dict: dict[str, Any],
                  package_id: str,
                  package_type: str = 'dataset') -> Markup:
    text = resource_display_name(resource_dict)
    url = url_for('{}_resource.read'.format(package_type),
                  id=package_id,
                  resource_id=resource_dict['id'])
    return link_to(text, url)


@core_helper
def tag_link(tag: dict[str, Any], package_type: str = 'dataset') -> Markup:
    url = url_for('{}.search'.format(package_type), tags=tag['name'])
    return link_to(tag.get('title', tag['name']), url)


@core_helper
def group_link(group: dict[str, Any]) -> Markup:
    url = url_for('group.read', id=group['name'])
    return link_to(group['title'], url)


@core_helper
def organization_link(organization: dict[str, Any]) -> Markup:
    url = url_for('organization.read', id=organization['name'])
    return link_to(organization['title'], url)


@core_helper
def dump_json(obj: Any, **kw: Any) -> str:
    return json.dumps(obj, **kw)


@core_helper
def snippet(template_name: str, **kw: Any) -> str:
    ''' This function is used to load html snippets into pages. keywords
    can be used to pass parameters into the snippet rendering '''
    import ckan.lib.base as base
    return base.render_snippet(template_name, **kw)


@core_helper
def convert_to_dict(object_type: str, objs: list[Any]) -> list[dict[str, Any]]:
    ''' This is a helper function for converting lists of objects into
    lists of dicts. It is for backwards compatability only. '''

    import ckan.lib.dictization.model_dictize as md
    converters = {'package': md.package_dictize}
    converter = converters[object_type]
    items = []
    context = cast(Context, {'model': model})
    for obj in objs:
        item = converter(obj, context)
        items.append(item)
    return items


# these are the types of objects that can be followed
_follow_objects = ['dataset', 'user', 'group']


@core_helper
def follow_button(obj_type: str, obj_id: str) -> str:
    '''Return a follow button for the given object type and id.

    If the user is not logged in return an empty string instead.

    :param obj_type: the type of the object to be followed when the follow
        button is clicked, e.g. 'user' or 'dataset'
    :type obj_type: string
    :param obj_id: the id of the object to be followed when the follow button
        is clicked
    :type obj_id: string

    :returns: a follow button as an HTML snippet
    :rtype: string

    '''
    obj_type = obj_type.lower()
    assert obj_type in _follow_objects
    # If the user is logged in show the follow/unfollow button
    user = current_user.name
    if user:
        context = cast(
            Context,
            {'model': model, 'session': model.Session, 'user': user})
        action = 'am_following_%s' % obj_type
        following = logic.get_action(action)(context, {'id': obj_id})
        return snippet('snippets/follow_button.html',
                       following=following,
                       obj_id=obj_id,
                       obj_type=obj_type)
    return ''


@core_helper
def follow_count(obj_type: str, obj_id: str) -> int:
    '''Return the number of followers of an object.

    :param obj_type: the type of the object, e.g. 'user' or 'dataset'
    :type obj_type: string
    :param obj_id: the id of the object
    :type obj_id: string

    :returns: the number of followers of the object
    :rtype: int

    '''
    obj_type = obj_type.lower()
    assert obj_type in _follow_objects
    action = '%s_follower_count' % obj_type
    context = cast(
        Context, {
            'model': model,
            'session': model.Session,
            'user': current_user.name
        }
    )
    return logic.get_action(action)(context, {'id': obj_id})


def _create_url_with_params(params: Optional[Iterable[tuple[str, Any]]] = None,
                            controller: Optional[str] = None,
                            action: Optional[str] = None,
                            extras: Optional[dict[str, Any]] = None):
    """internal function for building urls with parameters."""
    if not extras:
        if not controller and not action:
            # it's an url for the current page. Let's keep all interlal params,
            # like <package_type>
            extras = dict(request.view_args or {})
        else:
            extras = {}

    blueprint, view = p.toolkit.get_endpoint()
    if not controller:
        controller = getattr(g, "controller", blueprint)
    if not action:
        action = getattr(g, "action", view)

    assert controller is not None and action is not None
    endpoint = controller + "." + action
    url = url_for(endpoint, **extras)
    return _url_with_params(url, params)


@core_helper
def add_url_param(alternative_url: Optional[str] = None,
                  controller: Optional[str] = None,
                  action: Optional[str] = None,
                  extras: Optional[dict[str, Any]] = None,
                  new_params: Optional[dict[str, Any]] = None) -> str:
    '''
    Adds extra parameters to existing ones

    controller action & extras (dict) are used to create the base url via
    :py:func:`~ckan.lib.helpers.url_for` controller & action default to the
    current ones

    This can be overriden providing an alternative_url, which will be used
    instead.
    '''

    params_items = request.args.items(multi=True)
    params_nopage = [
        (k, v) for k, v in params_items
        if k != 'page'
    ]
    if new_params:
        params_nopage += list(new_params.items())
    if alternative_url:
        return _url_with_params(alternative_url, params_nopage)
    return _create_url_with_params(params=params_nopage, controller=controller,
                                   action=action, extras=extras)


@core_helper
def remove_url_param(key: Union[list[str], str],
                     value: Optional[str] = None,
                     replace: Optional[str] = None,
                     controller: Optional[str] = None,
                     action: Optional[str] = None,
                     extras: Optional[dict[str, Any]] = None,
                     alternative_url: Optional[str] = None) -> str:
    ''' Remove one or multiple keys from the current parameters.
    The first parameter can be either a string with the name of the key to
    remove or a list of keys to remove.
    A specific key/value pair can be removed by passing a second value
    argument otherwise all pairs matching the key will be removed. If replace
    is given then a new param key=replace will be added.
    Note that the value and replace parameters only apply to the first key
    provided (or the only one provided if key is a string).

    controller action & extras (dict) are used to create the base url
    via :py:func:`~ckan.lib.helpers.url_for`
    controller & action default to the current ones

    This can be overriden providing an alternative_url, which will be used
    instead.

    '''
    if isinstance(key, str):
        keys = [key]
    else:
        keys = key

    params_items = request.args.items(multi=True)
    params_nopage = [
        (k, v) for k, v in params_items
        if k != 'page'
    ]
    params = list(params_nopage)
    if value:
        params.remove((keys[0], value))
    else:
        for key in keys:
            for (k, v) in params[:]:
                if k == key:
                    params.remove((k, v))
    if replace is not None:
        params.append((keys[0], replace))

    if alternative_url:
        return _url_with_params(alternative_url, params)

    return _create_url_with_params(params=params, controller=controller,
                                   action=action, extras=extras)


@core_helper
def debug_inspect(arg: Any) -> Markup:
    ''' Output pprint.pformat view of supplied arg '''
    return literal('<pre>') + pprint.pformat(arg) + literal('</pre>')


@core_helper
def popular(type_: str,
            number: int,
            min: int = 1,
            title: Optional[str] = None) -> str:
    ''' display a popular icon. '''
    if type_ == 'views':
        title = ungettext('{number} view', '{number} views', number)
    elif type_ == 'recent views':
        title = ungettext('{number} recent view', '{number} recent views',
                          number)
    elif not title:
        raise Exception('popular() did not recieve a valid type_ or title')
    return snippet('snippets/popular.html',
                   title=title, number=number, min=min)


@core_helper
def groups_available(am_member: bool = False) -> list[dict[str, Any]]:
    '''Return a list of the groups that the user is authorized to edit.

    :param am_member: if True return only the groups the logged-in user is a
      member of, otherwise return all groups that the user is authorized to
      edit (for example, sysadmin users are authorized to edit all groups)
      (optional, default: False)
    :type am-member: bool

    '''
    context: Context = {}
    data_dict = {'available_only': True, 'am_member': am_member}
    return logic.get_action('group_list_authz')(context, data_dict)


@core_helper
def organizations_available(permission: str = 'manage_group',
                            include_dataset_count: bool = False
                            ) -> list[dict[str, Any]]:
    '''Return a list of organizations that the current user has the specified
    permission for.
    '''
    context: Context = {'user': current_user.name}
    data_dict = {
        'permission': permission,
        'include_dataset_count': include_dataset_count}
    return logic.get_action('organization_list_for_user')(context, data_dict)


@core_helper
def roles_translated() -> dict[str, str]:
    '''Return a dict of available roles with their translations'''
    return authz.roles_trans()


@core_helper
def user_in_org_or_group(group_id: str) -> bool:
    ''' Check if user is in a group or organization '''
    # we need a user
    if current_user.is_anonymous:
        return False
    # sysadmins can do anything
    if current_user.sysadmin:  # type: ignore
        return True
    query = model.Session.query(model.Member) \
        .filter(model.Member.state == 'active') \
        .filter(model.Member.table_name == 'user') \
        .filter(model.Member.group_id == group_id) \
        .filter(model.Member.table_id == current_user.id)  # type: ignore
    return len(query.all()) != 0


@core_helper
def escape_js(str_to_escape: str) -> str:
    '''Escapes special characters from a JS string.

       Useful e.g. when you need to pass JSON to the templates

       :param str_to_escape: string to be escaped
       :rtype: string
    '''
    return str_to_escape.replace('\\', '\\\\') \
        .replace('\'', '\\\'') \
        .replace('"', '\\\"')


@core_helper
def get_pkg_dict_extra(pkg_dict: dict[str, Any],
                       key: str,
                       default: Optional[Any] = None) -> Any:
    '''Returns the value for the dataset extra with the provided key.

    If the key is not found, it returns a default value, which is None by
    default.

    :param pkg_dict: dictized dataset
    :key: extra key to lookup
    :default: default value returned if not found
    '''

    extras = pkg_dict['extras'] if 'extras' in pkg_dict else []

    for extra in extras:
        if extra['key'] == key:
            return extra['value']

    return default


@core_helper
def get_request_param(parameter_name: str,
                      default: Optional[Any] = None) -> Any:
    ''' This function allows templates to access query string parameters
    from the request. This is useful for things like sort order in
    searches. '''
    return request.args.get(parameter_name, default)


# find all inner text of html eg `<b>moo</b>` gets `moo` but not of <a> tags
# as this would lead to linkifying links if they are urls.
RE_MD_GET_INNER_HTML = re.compile(
    r'(^|(?:<(?!a\b)[^>]*>))([^<]+)(?=<|$)',
    flags=re.UNICODE
)

# find all `internal links` eg. tag:moo, dataset:1234, tag:"my tag"
RE_MD_INTERNAL_LINK = re.compile(
    r'\b(tag|package|dataset|group):((")?(?(3)[ \w\-.]+|[\w\-.]+)(?(3)"))',
    flags=re.UNICODE
)

# find external links eg http://foo.com, https://bar.org/foobar.html
# but ignore trailing punctuation since it is probably not part of the link
RE_MD_EXTERNAL_LINK = re.compile(
    r'(\bhttps?:\/\/[\w\-\.,@?^=%&;:\/~\\+#]*'
    r'[\w\-@?^=%&:\/~\\+#]'  # but last character can't be punctuation [.,;]
    ')',
    flags=re.UNICODE
)

# find all tags but ignore < in the strings so that we can use it correctly
# in markdown
RE_MD_HTML_TAGS = re.compile('<[^><]*>')


@core_helper
def html_auto_link(data: str) -> str:
    '''Linkifies HTML

    `tag` converted to a tag link

    `dataset` converted to a dataset link

    `group` converted to a group link

    `http://` converted to a link
    '''

    link_fns: dict[str, Callable[[dict[str, str]], Markup]] = {
        'tag': tag_link,
        'group': group_link,
        'dataset': dataset_link,
        'package': dataset_link,
    }

    def makelink(matchobj: Match[str]):
        obj = matchobj.group(1)
        name = matchobj.group(2)
        title = '%s:%s' % (obj, name)
        return link_fns[obj]({'name': name.strip('"'), 'title': title})

    def link(matchobj: Match[str]):
        return '<a href="%s" target="_blank" rel="nofollow">%s</a>' \
            % (matchobj.group(1), matchobj.group(1))

    def process(matchobj: Match[str]):
        data = matchobj.group(2)
        data = RE_MD_INTERNAL_LINK.sub(makelink, data)
        data = RE_MD_EXTERNAL_LINK.sub(link, data)
        return matchobj.group(1) + data

    data = RE_MD_GET_INNER_HTML.sub(process, data)
    return data


@core_helper
def render_markdown(data: str,
                    auto_link: bool = True,
                    allow_html: bool = False) -> Union[str, Markup]:
    ''' Returns the data as rendered markdown

    :param auto_link: Should ckan specific links be created e.g. `group:xxx`
    :type auto_link: bool
    :param allow_html: If True then html entities in the markdown data.
        This is dangerous if users have added malicious content.
        If False all html tags are removed.
    :type allow_html: bool
    '''
    if not data:
        return ''
    if allow_html:
        data = markdown(data.strip())
    else:
        data = RE_MD_HTML_TAGS.sub('', data.strip())
        data = bleach_clean(
            markdown(data), strip=True,
            tags=MARKDOWN_TAGS,
            attributes=MARKDOWN_ATTRIBUTES)
    # tags can be added by tag:... or tag:"...." and a link will be made
    # from it
    if auto_link:
        data = html_auto_link(data)
    return literal(data)


@core_helper
def format_resource_items(
        items: list[tuple[str, Any]]) -> list[tuple[str, Any]]:
    ''' Take a resource item list and format nicely with blacklisting etc. '''
    blacklist = ['name', 'description', 'url', 'tracking_summary']
    output = []
    # regular expressions for detecting types in strings
    reg_ex_datetime = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{6})?$'
    reg_ex_int = r'^-?\d{1,}$'
    reg_ex_float = r'^-?\d{1,}\.\d{1,}$'
    for key, value in items:
        if (key in blacklist
                or (not isinstance(value, (int, float))
                    and not value)):
            # Ignore blocked keys and values that evaluate to
            # `bool(value) == False` (e.g. `""`, `[]` or `{}`),
            # with the exception of numbers such as `False`, `0`,`0.0`.
            continue
        # size is treated specially as we want to show in MiB etc
        if key == 'size':
            try:
                value = formatters.localised_filesize(int(value))
            except ValueError:
                # Sometimes values that can't be converted to ints can sneak
                # into the db. In this case, just leave them as they are.
                pass
        elif isinstance(value, str):
            # check if strings are actually datetime/number etc
            if re.search(reg_ex_datetime, value):
                datetime_ = date_str_to_datetime(value)
                value = formatters.localised_nice_date(datetime_)
            elif re.search(reg_ex_float, value):
                value = formatters.localised_number(float(value))
            elif re.search(reg_ex_int, value):
                value = formatters.localised_number(int(value))
        elif isinstance(value, bool):
            value = str(value)
        elif isinstance(value, (int, float)):
            value = formatters.localised_number(float(value))
        key = key.replace('_', ' ')
        output.append((key, value))
    return sorted(output, key=lambda x: x[0])


@core_helper
def get_allowed_view_types(
        resource: dict[str, Any],
        package: dict[str, Any]) -> list[tuple[str, str, str]]:
    data_dict = {'resource': resource, 'package': package}
    plugins = datapreview.get_allowed_view_plugins(data_dict)

    allowed_view_types: list[tuple[str, str, str]] = []
    for plugin in plugins:
        info = plugin.info()
        allowed_view_types.append((info['name'],
                                   info.get('title', info['name']),
                                   info.get('icon', 'image')))
    allowed_view_types.sort(key=lambda item: item[1])
    return allowed_view_types


@core_helper
def rendered_resource_view(resource_view: dict[str, Any],
                           resource: dict[str, Any],
                           package: dict[str, Any],
                           embed: bool = False) -> Markup:
    '''
    Returns a rendered resource view snippet.
    '''
    view_plugin = datapreview.get_view_plugin(resource_view['view_type'])
    assert view_plugin
    context: Context = {}
    data_dict = {'resource_view': resource_view,
                 'resource': resource,
                 'package': package}
    vars = view_plugin.setup_template_variables(context, data_dict) or {}
    template = view_plugin.view_template(context, data_dict)
    data_dict.update(vars)

    if not resource_view_is_iframed(resource_view) and embed:
        template = "package/snippets/resource_view_embed.html"

    import ckan.lib.base as base
    return literal(base.render(template, extra_vars=data_dict))


@core_helper
def view_resource_url(
        resource_view: dict[str, Any],
        resource: dict[str, Any],
        package: dict[str, Any],
        **kw: Any) -> str:
    '''
    Returns url for resource. made to be overridden by extensions. i.e
    by resource proxy.
    '''
    return resource['url']


@core_helper
def resource_view_is_filterable(resource_view: dict[str, Any]) -> bool:
    '''
    Returns True if the given resource view support filters.
    '''
    view_plugin = datapreview.get_view_plugin(resource_view['view_type'])
    assert view_plugin
    return view_plugin.info().get('filterable', False)


@core_helper
def resource_view_get_fields(resource: dict[str, Any]) -> list["str"]:
    '''Returns sorted list of text and time fields of a datastore resource.'''

    if not resource.get('datastore_active'):
        return []

    data = {
        'resource_id': resource['id'],
        'limit': 0,
        'include_total': False,
    }
    try:
        result = logic.get_action('datastore_search')({}, data)
    except logic.NotFound:
        return []

    fields = [field['id'] for field in result.get('fields', [])]

    return sorted(fields)


@core_helper
def resource_view_is_iframed(resource_view: dict[str, Any]) -> bool:
    '''
    Returns true if the given resource view should be displayed in an iframe.
    '''
    view_plugin = datapreview.get_view_plugin(resource_view['view_type'])
    assert view_plugin
    return view_plugin.info().get('iframed', True)


@core_helper
def resource_view_icon(resource_view: dict[str, Any]) -> str:
    '''
    Returns the icon for a particular view type.
    '''
    view_plugin = datapreview.get_view_plugin(resource_view['view_type'])
    assert view_plugin
    return view_plugin.info().get('icon', 'picture')


@core_helper
def resource_view_display_preview(resource_view: dict[str, Any]) -> bool:
    '''
    Returns if the view should display a preview.
    '''
    view_plugin = datapreview.get_view_plugin(resource_view['view_type'])
    assert view_plugin
    return view_plugin.info().get('preview_enabled', True)


@core_helper
def resource_view_full_page(resource_view: dict[str, Any]) -> bool:
    '''
    Returns if the edit view page should be full page.
    '''
    view_plugin = datapreview.get_view_plugin(resource_view['view_type'])
    assert view_plugin
    return view_plugin.info().get('full_page_edit', False)


@core_helper
def remove_linebreaks(string: str) -> str:
    '''Remove linebreaks from string to make it usable in JavaScript'''
    return str(string).replace('\n', '')


@core_helper
def list_dict_filter(list_: list[dict[str, Any]],
                     search_field: str, output_field: str,
                     value: Any) -> Any:
    ''' Takes a list of dicts and returns the value of a given key if the
    item has a matching value for a supplied key

    :param list_: the list to search through for matching items
    :type list_: list of dicts

    :param search_field: the key to use to find matching items
    :type search_field: string

    :param output_field: the key to use to output the value
    :type output_field: string

    :param value: the value to search for
    '''

    for item in list_:
        if item.get(search_field) == value:
            return item.get(output_field, value)
    return value


@core_helper
def SI_number_span(number: int) -> Markup:  # noqa
    ''' outputs a span with the number in SI unit eg 14700 -> 14.7k '''
    number = int(number)
    if number < 1000:
        output = literal('<span>')
    else:
        output = literal('<span title="' + formatters.localised_number(number)
                         + '">')
    return output + formatters.localised_SI_number(number) + literal('</span>')


# add some formatter functions
localised_number = formatters.localised_number
localised_SI_number = formatters.localised_SI_number  # noqa
localised_nice_date = formatters.localised_nice_date
localised_filesize = formatters.localised_filesize


@core_helper
def uploads_enabled() -> bool:
    if uploader.get_storage_path():
        return True
    return False


@core_helper
def get_featured_organizations(count: int = 1) -> list[dict[str, Any]]:
    '''Returns a list of favourite organization in the form
    of organization_list action function
    '''
    config_orgs = config.get('ckan.featured_orgs')
    orgs = featured_group_org(get_action='organization_show',
                              list_action='organization_list',
                              count=count,
                              items=config_orgs)
    return orgs


@core_helper
def get_featured_groups(count: int = 1) -> list[dict[str, Any]]:
    '''Returns a list of favourite group the form
    of organization_list action function
    '''
    config_groups = config.get('ckan.featured_groups')
    groups = featured_group_org(get_action='group_show',
                                list_action='group_list',
                                count=count,
                                items=config_groups)
    return groups


@core_helper
def featured_group_org(items: list[str], get_action: str, list_action: str,
                       count: int) -> list[dict[str, Any]]:
    def get_group(id: str):
        context: Context = {'ignore_auth': True,
                            'limits': {'packages': 2},
                            'for_view': True}
        data_dict = {'id': id,
                     'include_datasets': True}

        try:
            out = logic.get_action(get_action)(context, data_dict)
        except logic.NotFound:
            return None
        return out

    groups_data = []

    extras = logic.get_action(list_action)({}, {})

    # list of found ids to prevent duplicates
    found = []
    for group_name in items + extras:
        group = get_group(group_name)
        if not group:
            continue
        # check if duplicate
        if group['id'] in found:
            continue
        found.append(group['id'])
        groups_data.append(group)
        if len(groups_data) == count:
            break

    return groups_data


@core_helper
def get_site_statistics() -> dict[str, int]:
    stats = {}
    stats['dataset_count'] = logic.get_action('package_search')(
        {}, {"rows": 1})['count']
    stats['group_count'] = len(logic.get_action('group_list')({}, {}))
    stats['organization_count'] = len(
        logic.get_action('organization_list')({}, {}))
    return stats


_RESOURCE_FORMATS: dict[str, Any] = {}


def resource_formats_default_file():
    return os.path.join(
        os.path.dirname(os.path.realpath(ckan.config.__file__)),
        'resource_formats.json'
    )


@core_helper
def resource_formats() -> dict[str, list[str]]:
    ''' Returns the resource formats as a dict, sourced from the resource
    format JSON file.

    :param key:  potential user input value
    :param value:  [canonical mimetype lowercased, canonical format
                    (lowercase), human readable form]

    Fuller description of the fields are described in
    `ckan/config/resource_formats.json`.
    '''
    global _RESOURCE_FORMATS
    if not _RESOURCE_FORMATS:
        format_file_path = config.get('ckan.resource_formats')
        if not format_file_path:
            format_file_path = resource_formats_default_file()

        with open(format_file_path, encoding='utf-8') as format_file:
            try:
                file_resource_formats = json.loads(format_file.read())
            except ValueError as e:
                # includes simplejson.decoder.JSONDecodeError
                raise ValueError('Invalid JSON syntax in %s: %s' %
                                 (format_file_path, e))

            for format_line in file_resource_formats:
                if format_line[0] == '_comment':
                    continue
                line = [format_line[2], format_line[0], format_line[1]]
                alternatives = format_line[3] if len(format_line) == 4 else []
                for item in line + alternatives:
                    if item:
                        item = item.lower()
                        if item in _RESOURCE_FORMATS \
                                and _RESOURCE_FORMATS[item] != line:
                            raise ValueError('Duplicate resource format '
                                             'identifier in %s: %s' %
                                             (format_file_path, item))
                        _RESOURCE_FORMATS[item] = line

    return _RESOURCE_FORMATS


@core_helper
def unified_resource_format(format: str) -> str:
    formats = resource_formats()
    format_clean = format.lower()
    if format_clean in formats:
        format_new = formats[format_clean][1]
    else:
        format_new = format
    return format_new


@core_helper
def check_config_permission(permission: str) -> Union[list[str], bool]:
    return authz.check_config_permission(permission)


@core_helper
def get_organization(org: Optional[str] = None,
                     include_datasets: bool = False) -> dict[str, Any]:
    if org is None:
        return {}
    try:
        return logic.get_action('organization_show')(
            {}, {'id': org, 'include_datasets': include_datasets})
    except (logic.NotFound, logic.ValidationError, logic.NotAuthorized):
        return {}


@core_helper
def license_options(
    existing_license_id: Optional[tuple[str, str]] = None
) -> list[tuple[str, str]]:
    '''Returns [(l.title, l.id), ...] for the licenses configured to be
    offered. Always includes the existing_license_id, if supplied.
    '''
    register = model.Package.get_license_register()
    sorted_licenses = sorted(register.values(), key=lambda x: x.title)
    license_ids = [license.id for license in sorted_licenses]
    if existing_license_id and existing_license_id not in license_ids:
        license_ids.insert(0, existing_license_id)
    return [
        (license_id,
         _(register[license_id].title)
         if license_id in register else license_id)
        for license_id in license_ids]


@core_helper
def get_translated(data_dict: dict[str, Any], field: str) -> Union[str, Any]:
    language = i18n.get_lang()
    try:
        return data_dict[field + u'_translated'][language]
    except KeyError:
        pass
    # Check the base language, en_GB->en
    try:
        base_language = language.split('_')[0]
        if base_language != language:
            return data_dict[field + u'_translated'][base_language]
    except KeyError:
        pass
    return data_dict.get(field, '')


@core_helper
def facets() -> list[str]:
    u'''Returns a list of the current facet names'''
    return config.get(u'search.facets')


@core_helper
def mail_to(email_address: str, name: str) -> Markup:
    email = escape(email_address)
    author = escape(name)
    html = Markup(u'<a href=mailto:{0}>{1}</a>'.format(email, author))
    return html


@core_helper
def clean_html(html: Any) -> str:
    return bleach_clean(str(html))


core_helper(flash, name='flash')
core_helper(localised_number)
core_helper(localised_SI_number)
core_helper(localised_nice_date)
core_helper(localised_filesize)
core_helper(plugin_loaded)
# Useful additionsfrom the i18n library.
core_helper(i18n.get_available_locales)
core_helper(i18n.get_locales_dict)
core_helper(literal)
# Useful additions from the paste library.
core_helper(asbool)
# Useful additions from the stdlib.
core_helper(urlencode)
core_helper(include_asset)
core_helper(render_assets)


def load_plugin_helpers() -> None:
    """
    (Re)loads the list of helpers provided by plugins.
    """
    global helper_functions

    helper_functions.clear()
    helper_functions.update(_builtin_functions)
    chained_helpers = defaultdict(list)

    for plugin in p.PluginImplementations(p.ITemplateHelpers):
        for name, func in plugin.get_helpers().items():
            if _is_chained_helper(func):
                chained_helpers[name].append(func)
            else:
                helper_functions[name] = func
    for name, func_list in chained_helpers.items():
        if name not in helper_functions:
            raise logic.NotFound(
                u'The helper %r is not found for chained helper' % (name))
        for func in reversed(func_list):
            new_func = functools.partial(
                func, helper_functions[name])
            # persisting attributes to the new partial function
            for attribute, value in func.__dict__.items():
                setattr(new_func, attribute, value)
            helper_functions[name] = new_func


@core_helper
def sanitize_id(id_: str) -> str:
    '''Given an id (uuid4), if it has any invalid characters it raises
    ValueError.
    '''
    return str(uuid.UUID(id_))


@core_helper
def get_collaborators(package_id: str) -> list[tuple[str, str]]:
    '''Return the collaborators list for a dataset

    Returns a list of tuples with the user id and the capacity
    '''
    context: Context = {
        'ignore_auth': True,
        'user': current_user.name}
    data_dict = {'id': package_id}
    _collaborators = logic.get_action('package_collaborator_list')(
        context, data_dict)

    collaborators = []

    for collaborator in _collaborators:
        collaborators.append((
            collaborator['user_id'],
            collaborator['capacity']
        ))

    return collaborators


@core_helper
def can_update_owner_org(
        package_dict: dict[str, Any],
        user_orgs: Optional[list[dict[str, Any]]] = None) -> bool:

    if not package_dict.get('id') or not package_dict.get('owner_org'):
        # We are either creating a dataset or it is an unowned dataset.
        # In both cases we defer to the other auth settings
        return True

    if not user_orgs:
        user_orgs = organizations_available('create_dataset')

    if package_dict['owner_org'] in [o['id'] for o in user_orgs]:
        # Admins and editors of the current org can change it
        return True

    collaborators_can_change_owner_org = authz.check_config_permission(
        'allow_collaborators_to_change_owner_org')

    user = model.User.get(current_user.name)

    if (user
            and authz.check_config_permission('allow_dataset_collaborators')
            and collaborators_can_change_owner_org
            and user.id in [
                co[0] for co in get_collaborators(package_dict['id'])
            ]):

        # User is a collaborator and changing the owner_org is allowed via
        # config
        return True

    return False


@core_helper
def decode_view_request_filters() -> dict[str, Any] | None:
    filterString = request.args.get('filters')
    if request.form.get('filters') is not None:
        filterString = request.form.get('filters')
    if filterString is not None and len(filterString) > 0:
        filters = {}
        for k_v in filterString.split(u'|'):
            k, _sep, v = k_v.partition(u':')
            if unquote(str(k)) in filters:
                if unquote(str(v)) not in filters[unquote(str(k))]:
                    filters[unquote(str(k))].append(unquote(str(v)))
            else:
                filters.setdefault(unquote(str(k)), []).append(unquote(str(v)))
        return filters
    return None


@core_helper
def check_ckan_version(min_version: Optional[str] = None,
                       max_version: Optional[str] = None):
    """Return ``True`` if the CKAN version is greater than or equal to
    ``min_version`` and less than or equal to ``max_version``,
    return ``False`` otherwise.

    If no ``min_version`` is given, just check whether the CKAN version is
    less than or equal to ``max_version``.

    If no ``max_version`` is given, just check whether the CKAN version is
    greater than or equal to ``min_version``.

    :param min_version: the minimum acceptable CKAN version,
        eg. ``'2.1'``
    :type min_version: string

    :param max_version: the maximum acceptable CKAN version,
        eg. ``'2.3'``
    :type max_version: string

    """
    return p.toolkit.check_ckan_version(min_version=min_version,
                                        max_version=max_version)


def make_login_url(
    login_view: str, next_url: Optional[str] = None, next_field: str = "next"
) -> str:
    '''
    Creates a URL for redirecting to a login page. If only `login_view` is
    provided, this will just return the URL for it. If `next_url` is provided,
    however, this will append a ``next=URL`` parameter to the query string
    so that the login view can redirect back to that URL.
    '''
    base = login_view
    if next_url is None:
        return base

    if url_is_local(next_url):
        md = {}
        md[next_field] = urlparse(next_url).path
        parsed_base = urlparse(base)
        netloc = parsed_base.netloc
        parsed_base = parsed_base._replace(netloc=netloc, query=urlencode(md))
        return urlunparse(parsed_base)
    return base


@core_helper
def csrf_input():
    return snippet('snippets/csrf_input.html')
