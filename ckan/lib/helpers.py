# encoding: utf-8

'''Helper functions

Consists of functions to typically be used within templates, but also
available to Controllers. This module is available to templates as 'h'.
'''
import email.utils
import datetime
import logging
import re
import os
import pytz
import tzlocal
import urllib
import pprint
import copy
import urlparse
from urllib import urlencode
import uuid

from paste.deploy import converters
from webhelpers.html import HTML, literal, tags, tools
from webhelpers import paginate
import webhelpers.text as whtext
import webhelpers.date as date
from markdown import markdown
from bleach import clean as bleach_clean, ALLOWED_TAGS, ALLOWED_ATTRIBUTES
from pylons import url as _pylons_default_url
from ckan.common import config, is_flask_request
from flask import redirect as _flask_redirect
from flask import _request_ctx_stack, current_app
from routes import redirect_to as _routes_redirect_to
from routes import url_for as _routes_default_url_for
from flask import url_for as _flask_default_url_for
from werkzeug.routing import BuildError as FlaskRouteBuildError
import i18n
from six import string_types, text_type

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

from ckan.common import _, ungettext, c, g, request, session, json
from markupsafe import Markup, escape


log = logging.getLogger(__name__)

DEFAULT_FACET_NAMES = u'organization groups tags res_format license_id'

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
    'organizations_index': 'organization.index'
}


class HelperAttributeDict(dict):
    def __init__(self, *args, **kwargs):
        super(HelperAttributeDict, self).__init__(*args, **kwargs)
        self.__dict__ = self

    def __getitem__(self, key):
        try:
            value = super(HelperAttributeDict, self).__getitem__(key)
        except KeyError:
            raise ckan.exceptions.HelperError(
                'Helper \'{key}\' has not been defined.'.format(
                    key=key
                )
            )
        return value


# Builtin helper functions.
_builtin_functions = {}
helper_functions = HelperAttributeDict()


def core_helper(f, name=None):
    """
    Register a function as a builtin helper method.
    """
    def _get_name(func_or_class):
        # Handles both methods and class instances.
        try:
            return func_or_class.__name__
        except AttributeError:
            return func_or_class.__class__.__name__

    _builtin_functions[name or _get_name(f)] = f
    return f


def _datestamp_to_datetime(datetime_):
    ''' Converts a datestamp to a datetime.  If a datetime is provided it
    just gets returned.

    :param datetime_: the timestamp
    :type datetime_: string or datetime

    :rtype: datetime
    '''
    if isinstance(datetime_, string_types):
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
def redirect_to(*args, **kw):
    '''Issue a redirect: return an HTTP response with a ``302 Moved`` header.

    This is a wrapper for :py:func:`routes.redirect_to` that maintains the
    user's selected language when redirecting.

    The arguments to this function identify the route to redirect to, they're
    the same arguments as :py:func:`ckan.plugins.toolkit.url_for` accepts,
    for example::

        import ckan.plugins.toolkit as toolkit

        # Redirect to /dataset/my_dataset.
        toolkit.redirect_to(controller='package', action='read',
                            id='my_dataset')

    Or, using a named route::

        toolkit.redirect_to('dataset_read', id='changed')

    If given a single string as argument, this redirects without url parsing

        toolkit.redirect_to('http://example.com')
        toolkit.redirect_to('/dataset')
        toolkit.redirect_to('/some/other/path')

    '''
    if are_there_flash_messages():
        kw['__no_cache__'] = True

    # Routes router doesn't like unicode args
    uargs = map(lambda arg: str(arg) if isinstance(arg, text_type) else arg,
                args)

    _url = ''
    skip_url_parsing = False
    parse_url = kw.pop('parse_url', False)
    if uargs and len(uargs) is 1 and isinstance(uargs[0], string_types) \
            and (uargs[0].startswith('/') or is_url(uargs[0])) \
            and parse_url is False:
        skip_url_parsing = True
        _url = uargs[0]

    if skip_url_parsing is False:
        _url = url_for(*uargs, **kw)

    if _url.startswith('/'):
        _url = str(config['ckan.site_url'].rstrip('/') + _url)

    if is_flask_request():
        return _flask_redirect(_url)
    else:
        return _routes_redirect_to(_url)


@maintain.deprecated('h.url is deprecated please use h.url_for')
@core_helper
def url(*args, **kw):
    '''
    Deprecated: please use `url_for` instead
    '''
    return url_for(*args, **kw)


@core_helper
def get_site_protocol_and_host():
    '''Return the protocol and host of the configured `ckan.site_url`.
    This is needed to generate valid, full-qualified URLs.

    If `ckan.site_url` is set like this::

        ckan.site_url = http://example.com

    Then this function would return a tuple `('http', 'example.com')`
    If the setting is missing, `(None, None)` is returned instead.

    '''
    site_url = config.get('ckan.site_url', None)
    if site_url is not None:
        parsed_url = urlparse.urlparse(site_url)
        return (
            parsed_url.scheme.encode('utf-8'),
            parsed_url.netloc.encode('utf-8')
        )
    return (None, None)


def _get_auto_flask_context():
    '''
    Provides a Flask test request context if we are outside the context
    of a web request (tests or CLI)
    '''

    from ckan.config.middleware import _internal_test_request_context
    from ckan.lib.cli import _cli_test_request_context

    # This is a normal web request, there is a request context present
    if _request_ctx_stack.top:
        return None

    # We are outside a web request. A test web application was created
    # (and with it a test request context with the relevant configuration)
    if _internal_test_request_context:
        return _internal_test_request_context

    # We are outside a web request. This is a CLI command. A test request
    # context was created when setting it up
    if _cli_test_request_context:
        return _cli_test_request_context


@core_helper
def url_for(*args, **kw):
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

        url_for(controller='package', action='read', id='my_dataset')
        # Returns '/dataset/my_dataset'

    Or, using a named route::

        url_for('dataset_read', id='changed')
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

        # If it doesn't succeed, fallback to the Pylons router
        my_url = _url_for_pylons(*args, **kw)
    finally:
        if _auto_flask_context:
            _auto_flask_context.pop()

    # Add back internal params
    kw['__ckan_no_root'] = no_root

    # Rewrite the URL to take the locale and root_path into account
    return _local_url(my_url, locale=locale, **kw)


def _url_for_flask(*args, **kw):
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
            isinstance(kw.get('ver'), string_types) and
            kw['ver'].startswith('/')):
        kw['ver'] = kw['ver'].replace('/', '')

    # Try to build the URL with flask.url_for
    my_url = _flask_default_url_for(*args, **kw)

    if external:
        # Don't rely on the host generated by Flask, as SERVER_NAME might not
        # be set or might be not be up to date (as in tests changing
        # `ckan.site_url`). Contrary to the Routes mapper, there is no way in
        # Flask to pass the host explicitly, so we rebuild the URL manually
        # based on `ckan.site_url`, which is essentially what we did on Pylons
        protocol, host = get_site_protocol_and_host()
        parts = urlparse.urlparse(my_url)
        my_url = urlparse.urlunparse((protocol, host, parts.path, parts.params,
                                      parts.query, parts.fragment))

    return my_url


def _url_for_pylons(*args, **kw):
    '''Build a URL using the Pylons (Routes) router

    This function should not be called directly, use ``url_for`` instead
    '''

    # We need to provide protocol and host to get full URLs, get them from
    # ckan.site_url
    if kw.pop('_external', None):
        kw['qualified'] = True
    if kw.get('qualified'):
        kw['protocol'], kw['host'] = get_site_protocol_and_host()

    # The Pylons API routes require a slask on the version number for some
    # reason
    if kw.get('controller') == 'api' and kw.get('ver'):
        if (isinstance(kw['ver'], int) or
                not kw['ver'].startswith('/')):
            kw['ver'] = '/%s' % kw['ver']

    # Try to build the URL with routes.url_for
    return _routes_default_url_for(*args, **kw)


@core_helper
def url_for_static(*args, **kw):
    '''Returns the URL for static content that doesn't get translated (eg CSS)

    It'll raise CkanUrlException if called with an external URL

    This is a wrapper for :py:func:`routes.url_for`
    '''
    if args:
        url = urlparse.urlparse(args[0])
        url_is_external = (url.scheme != '' or url.netloc != '')
        if url_is_external:
            CkanUrlException = ckan.exceptions.CkanUrlException
            raise CkanUrlException('External URL passed to url_for_static()')
    return url_for_static_or_external(*args, **kw)


@core_helper
def url_for_static_or_external(*args, **kw):
    '''Returns the URL for static content that doesn't get translated (eg CSS),
    or external URLs

    This is a wrapper for :py:func:`routes.url_for`
    '''
    def fix_arg(arg):
        url = urlparse.urlparse(str(arg))
        url_is_relative = (url.scheme == '' and url.netloc == '' and
                           not url.path.startswith('/'))
        if url_is_relative:
            return '/' + url.geturl()
        return url.geturl()

    if args:
        args = (fix_arg(args[0]), ) + args[1:]
    if kw.get('qualified', False):
        kw['protocol'], kw['host'] = get_site_protocol_and_host()
    my_url = _routes_default_url_for(*args, **kw)
    return _local_url(my_url, locale='default', **kw)


@core_helper
def is_url(*args, **kw):
    '''
    Returns True if argument parses as a http, https or ftp URL
    '''
    if not args:
        return False
    try:
        url = urlparse.urlparse(args[0])
    except ValueError:
        return False

    default_valid_schemes = ('http', 'https', 'ftp')

    valid_schemes = config.get('ckan.valid_url_schemes', '').lower().split()

    return url.scheme in (valid_schemes or default_valid_schemes)


def _local_url(url_to_amend, **kw):
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
        root = _routes_default_url_for('/',
                                       qualified=True,
                                       host=host,
                                       protocol=protocol)[:-1]
    # ckan.root_path is defined when we have none standard language
    # position in the url
    root_path = config.get('ckan.root_path', None)
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
def url_is_local(url):
    '''Returns True if url is local'''
    if not url or url.startswith('//'):
        return False
    parsed = urlparse.urlparse(url)
    if parsed.scheme:
        domain = urlparse.urlparse(url_for('/', qualified=True)).netloc
        if domain != parsed.netloc:
            return False
    return True


@core_helper
def full_current_url():
    ''' Returns the fully qualified current url (eg http://...) useful
    for sharing etc '''
    return (url_for(request.environ['CKAN_CURRENT_URL'], qualified=True))


@core_helper
def current_url():
    ''' Returns current url unquoted'''
    return urllib.unquote(request.environ['CKAN_CURRENT_URL'])


@core_helper
def lang():
    ''' Return the language code for the current locale eg `en` '''
    return request.environ.get('CKAN_LANG')


@core_helper
def ckan_version():
    '''Return CKAN version'''
    return ckan.__version__


@core_helper
def lang_native_name(lang=None):
    ''' Return the language name currently used in it's localised form
        either from parameter or current environ setting'''
    lang = lang or lang()
    locale = i18n.get_locales_dict().get(lang)
    if locale:
        return locale.display_name or locale.english_name
    return lang


@core_helper
def is_rtl_language():
    return lang() in config.get('ckan.i18n.rtl_languages',
                                'he ar fa_IR').split()


@core_helper
def get_rtl_css():
    rtl_css = config.get('ckan.i18n.rtl_css', None)
    if not rtl_css:
        main_css = config.get('ckan.main_css', '/base/css/main.css')
        rtl_css = main_css.replace('.css', '-rtl.css')
    return rtl_css


class Message(object):
    '''A message returned by ``Flash.pop_messages()``.

    Converting the message to a string returns the message text. Instances
    also have the following attributes:

    * ``message``: the message text.
    * ``category``: the category specified when the message was created.
    '''

    def __init__(self, category, message, allow_html):
        self.category = category
        self.message = message
        self.allow_html = allow_html

    def __str__(self):
        return self.message

    __unicode__ = __str__

    def __html__(self):
        if self.allow_html:
            return self.message
        else:
            return escape(self.message)


class _Flash(object):

    # List of allowed categories.  If None, allow any category.
    categories = ["", "alert-info", "alert-error", "alert-success"]

    # Default category if none is specified.
    default_category = ""

    def __init__(self, session_key="flash", categories=None,
                 default_category=None):
        self.session_key = session_key
        if categories is not None:
            self.categories = categories
        if default_category is not None:
            self.default_category = default_category
        if self.categories and self.default_category not in self.categories:
            raise ValueError("unrecognized default category %r"
                             % (self.default_category, ))

    def __call__(self, message, category=None, ignore_duplicate=False,
                 allow_html=False):
        if not category:
            category = self.default_category
        elif self.categories and category not in self.categories:
            raise ValueError("unrecognized category %r" % (category, ))
        # Don't store Message objects in the session, to avoid unpickling
        # errors in edge cases.
        new_message_tuple = (category, message, allow_html)
        messages = session.setdefault(self.session_key, [])
        # ``messages`` is a mutable list, so changes to the local variable are
        # reflected in the session.
        if ignore_duplicate:
            for i, m in enumerate(messages):
                if m[1] == message:
                    if m[0] != category:
                        messages[i] = new_message_tuple
                        session.save()
                    return  # Original message found, so exit early.
        messages.append(new_message_tuple)
        session.save()

    def pop_messages(self):
        messages = session.pop(self.session_key, [])
        # only save session if it has changed
        if messages:
            session.save()
        return [Message(*m) for m in messages]

    def are_there_messages(self):
        return bool(session.get(self.session_key))


flash = _Flash()
# this is here for backwards compatability
_flash = flash


@core_helper
def flash_notice(message, allow_html=False):
    ''' Show a flash message of type notice '''
    flash(message, category='alert-info', allow_html=allow_html)


@core_helper
def flash_error(message, allow_html=False):
    ''' Show a flash message of type error '''
    flash(message, category='alert-error', allow_html=allow_html)


@core_helper
def flash_success(message, allow_html=False):
    ''' Show a flash message of type success '''
    flash(message, category='alert-success', allow_html=allow_html)


@core_helper
def are_there_flash_messages():
    ''' Returns True if there are flash messages for the current user '''
    return flash.are_there_messages()


def _link_active(kwargs):
    ''' creates classes for the link_to calls '''
    if is_flask_request():
        return _link_active_flask(kwargs)
    else:
        return _link_active_pylons(kwargs)


def _link_active_pylons(kwargs):
    highlight_actions = kwargs.get('highlight_actions',
                                   kwargs.get('action', '')).split()
    return (c.controller == kwargs.get('controller')
            and c.action in highlight_actions)


def _link_active_flask(kwargs):
    blueprint, endpoint = request.url_rule.endpoint.split('.')
    return(kwargs.get('controller') == blueprint and
           kwargs.get('action') == endpoint)


def _link_to(text, *args, **kwargs):
    '''Common link making code for several helper functions'''
    assert len(args) < 2, 'Too many unnamed arguments'

    def _link_class(kwargs):
        ''' creates classes for the link_to calls '''
        suppress_active_class = kwargs.pop('suppress_active_class', False)
        if not suppress_active_class and _link_active(kwargs):
            active = ' active'
        else:
            active = ''
        kwargs.pop('highlight_actions', '')
        return kwargs.pop('class_', '') + active or None

    def _create_link_text(text, **kwargs):
        ''' Update link text to add a icon or span if specified in the
        kwargs '''
        if kwargs.pop('inner_span', None):
            text = literal('<span>') + text + literal('</span>')
        if icon:
            text = literal('<i class="fa fa-%s"></i> ' % icon) + text
        return text

    icon = kwargs.pop('icon', None)
    class_ = _link_class(kwargs)
    return tags.link_to(
        _create_link_text(text, **kwargs),
        url_for(*args, **kwargs),
        class_=class_
    )


@core_helper
def nav_link(text, *args, **kwargs):
    '''
    :param class_: pass extra class(es) to add to the ``<a>`` tag
    :param icon: name of ckan icon to use within the link
    :param condition: if ``False`` then no link is returned

    '''
    if is_flask_request():
        return nav_link_flask(text, *args, **kwargs)
    else:
        return nav_link_pylons(text, *args, **kwargs)


def nav_link_flask(text, *args, **kwargs):
    if len(args) > 1:
        raise Exception('Too many unnamed parameters supplied')
    blueprint, endpoint = request.url_rule.endpoint.split('.')
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


def nav_link_pylons(text, *args, **kwargs):
    if len(args) > 1:
        raise Exception('Too many unnamed parameters supplied')
    if args:
        kwargs['controller'] = kwargs.get('controller')
        log.warning('h.nav_link() please supply controller as a named '
                    'parameter not a positional one')
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
@maintain.deprecated('h.nav_named_link is deprecated please '
                     'use h.nav_link\nNOTE: you will need to pass the '
                     'route_name as a named parameter')
def nav_named_link(text, named_route, **kwargs):
    '''Create a link for a named route.
    Deprecated in ckan 2.0 '''
    return nav_link(text, named_route=named_route, **kwargs)


@core_helper
@maintain.deprecated('h.subnav_link is deprecated please '
                     'use h.nav_link\nNOTE: if action is passed as the second '
                     'parameter make sure it is passed as a named parameter '
                     'eg. `action=\'my_action\'')
def subnav_link(text, action, **kwargs):
    '''Create a link for a named route.
    Deprecated in ckan 2.0 '''
    kwargs['action'] = action
    return nav_link(text, **kwargs)


@core_helper
@maintain.deprecated('h.subnav_named_route is deprecated please '
                     'use h.nav_link\nNOTE: you will need to pass the '
                     'route_name as a named parameter')
def subnav_named_route(text, named_route, **kwargs):
    '''Generate a subnav element based on a named route
    Deprecated in ckan 2.0 '''
    return nav_link(text, named_route=named_route, **kwargs)


@core_helper
def build_nav_main(*args):
    ''' build a set of menu items.

    args: tuples of (menu type, title) eg ('login', _('Login'))
    outputs <li><a href="...">title</a></li>
    '''
    output = ''
    for item in args:
        menu_item, title = item[:2]
        if len(item) == 3 and not check_access(item[2]):
            continue
        output += _make_menu_item(menu_item, title)
    return output


@core_helper
def build_nav_icon(menu_item, title, **kw):
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
def build_nav(menu_item, title, **kw):
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


# Legacy route names
LEGACY_ROUTE_NAMES = {
    'home': 'home.index',
    'about': 'home.about',
}


def map_pylons_to_flask_route_name(menu_item):
    '''returns flask routes for old fashioned route names'''
    # Pylons to Flask legacy route names mappings
    mappings = config.get('ckan.legacy_route_mappings')
    if mappings:
        if isinstance(mappings, string_types):
            LEGACY_ROUTE_NAMES.update(json.loads(mappings))
        elif isinstance(mappings, dict):
            LEGACY_ROUTE_NAMES.update(mappings)

    if menu_item in LEGACY_ROUTE_NAMES:
        log.info('Route name "{}" is deprecated and will be removed.\
                Please update calls to use "{}" instead'.format(
                menu_item, LEGACY_ROUTE_NAMES[menu_item]))
    return LEGACY_ROUTE_NAMES.get(menu_item, menu_item)


@core_helper
def build_extra_admin_nav():
    '''Build extra navigation items used in ``admin/base.html`` for values
    defined in the config option ``ckan.admin_tabs``. Typically this is
    populated by extensions.

    :rtype: HTML literal

    '''
    admin_tabs_dict = config.get('ckan.admin_tabs')
    output = ''
    if admin_tabs_dict:
        for key in admin_tabs_dict:
            output += build_nav_icon(key, admin_tabs_dict[key])
    return output


def _make_menu_item(menu_item, title, **kw):
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
    menu_item = map_pylons_to_flask_route_name(menu_item)
    _menu_items = config['routes.named_routes']
    if menu_item not in _menu_items:
        raise Exception('menu item `%s` cannot be found' % menu_item)
    item = copy.copy(_menu_items[menu_item])
    item.update(kw)
    active = _link_active(item)
    needed = item.pop('needed')
    for need in needed:
        if need not in kw:
            raise Exception('menu item `%s` need parameter `%s`'
                            % (menu_item, need))
    link = _link_to(title, menu_item, suppress_active_class=True, **item)
    if active:
        return literal('<li class="active">') + link + literal('</li>')
    return literal('<li>') + link + literal('</li>')


@core_helper
def default_group_type():
    return str(config.get('ckan.default.group_type', 'group'))


@core_helper
def get_facet_items_dict(facet, limit=None, exclude_active=False):
    '''Return the list of unselected facet items for the given facet, sorted
    by count.

    Returns the list of unselected facet contraints or facet items (e.g. tag
    names like "russian" or "tolstoy") for the given search facet (e.g.
    "tags"), sorted by facet item count (i.e. the number of search results that
    match each facet item).

    Reads the complete list of facet items for the given facet from
    c.search_facets, and filters out the facet items that the user has already
    selected.

    Arguments:
    facet -- the name of the facet to filter.
    limit -- the max. number of facet items to return.
    exclude_active -- only return unselected facets.

    '''
    if not hasattr(c, u'search_facets') or not c.search_facets.get(
                                               facet, {}).get(u'items'):
        return []
    facets = []
    for facet_item in c.search_facets.get(facet)['items']:
        if not len(facet_item['name'].strip()):
            continue
        if not (facet, facet_item['name']) in request.params.items():
            facets.append(dict(active=False, **facet_item))
        elif not exclude_active:
            facets.append(dict(active=True, **facet_item))
    # Sort descendingly by count and ascendingly by case-sensitive display name
    facets.sort(key=lambda it: (-it['count'], it['display_name'].lower()))
    if hasattr(c, 'search_facets_limits'):
        if c.search_facets_limits and limit is None:
            limit = c.search_facets_limits.get(facet)
    # zero treated as infinite for hysterical raisins
    if limit is not None and limit > 0:
        return facets[:limit]
    return facets


@core_helper
def has_more_facets(facet, limit=None, exclude_active=False):
    '''
    Returns True if there are more facet items for the given facet than the
    limit.

    Reads the complete list of facet items for the given facet from
    c.search_facets, and filters out the facet items that the user has already
    selected.

    Arguments:
    facet -- the name of the facet to filter.
    limit -- the max. number of facet items.
    exclude_active -- only return unselected facets.

    '''
    facets = []
    for facet_item in c.search_facets.get(facet)['items']:
        if not len(facet_item['name'].strip()):
            continue
        if not (facet, facet_item['name']) in request.params.items():
            facets.append(dict(active=False, **facet_item))
        elif not exclude_active:
            facets.append(dict(active=True, **facet_item))
    if c.search_facets_limits and limit is None:
        limit = c.search_facets_limits.get(facet)
    if limit is not None and len(facets) > limit:
        return True
    return False


@core_helper
def unselected_facet_items(facet, limit=10):
    '''Return the list of unselected facet items for the given facet, sorted
    by count.

    Returns the list of unselected facet contraints or facet items (e.g. tag
    names like "russian" or "tolstoy") for the given search facet (e.g.
    "tags"), sorted by facet item count (i.e. the number of search results that
    match each facet item).

    Reads the complete list of facet items for the given facet from
    c.search_facets, and filters out the facet items that the user has already
    selected.

    Arguments:
    facet -- the name of the facet to filter.
    limit -- the max. number of facet items to return.

    '''
    return get_facet_items_dict(facet, limit=limit, exclude_active=True)


@core_helper
@maintain.deprecated('h.get_facet_title is deprecated in 2.0 and will be '
                     'removed.')
def get_facet_title(name):
    '''Deprecated in ckan 2.0 '''
    # if this is set in the config use this
    config_title = config.get('search.facets.%s.title' % name)
    if config_title:
        return config_title

    facet_titles = {'organization': _('Organizations'),
                    'groups': _('Groups'),
                    'tags': _('Tags'),
                    'res_format': _('Formats'),
                    'license': _('Licenses'), }
    return facet_titles.get(name, name.capitalize())


@core_helper
def get_param_int(name, default=10):
    try:
        return int(request.params.get(name, default))
    except ValueError:
        return default


def _url_with_params(url, params):
    if not params:
        return url
    params = [(k, v.encode('utf-8') if isinstance(v, string_types) else str(v))
              for k, v in params]
    return url + u'?' + urlencode(params)


def _search_url(params):
    url = url_for(controller='package', action='search')
    return _url_with_params(url, params)


@core_helper
def sorted_extras(package_extras, auto_clean=False, subs=None, exclude=None):
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
        exclude = config.get('package_hide_extras', [])
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
            v = ", ".join(map(text_type, v))
        output.append((k, v))
    return output


@core_helper
def check_access(action, data_dict=None):
    if not getattr(g, u'user', None):
        g.user = ''
    context = {'model': model,
               'user': g.user}
    if not data_dict:
        data_dict = {}
    try:
        logic.check_access(action, context, data_dict)
        authorized = True
    except logic.NotAuthorized:
        authorized = False

    return authorized


@core_helper
@maintain.deprecated("helpers.get_action() is deprecated and will be removed "
                     "in a future version of CKAN. Instead, please use the "
                     "extra_vars param to render() in your controller to pass "
                     "results from action functions to your templates.")
def get_action(action_name, data_dict=None):
    '''Calls an action function from a template. Deprecated in CKAN 2.3.'''
    if data_dict is None:
        data_dict = {}
    return logic.get_action(action_name)({}, data_dict)


@core_helper
def linked_user(user, maxlength=0, avatar=20):
    if not isinstance(user, model.User):
        user_name = text_type(user)
        user = model.User.get(user_name)
        if not user:
            return user_name
    if user:
        name = user.name if model.User.VALID_NAME.match(user.name) else user.id
        displayname = user.display_name

        if maxlength and len(user.display_name) > maxlength:
            displayname = displayname[:maxlength] + '...'

        return tags.literal(u'{icon} {link}'.format(
            icon=gravatar(
                email_hash=user.email_hash,
                size=avatar
            ),
            link=tags.link_to(
                displayname,
                url_for('user.read', id=name)
            )
        ))


@core_helper
def group_name_to_title(name):
    group = model.Group.by_name(name)
    if group is not None:
        return group.display_name
    return name


@core_helper
def markdown_extract(text, extract_length=190):
    ''' return the plain text representation of markdown encoded text.  That
    is the texted without any html tags.  If extract_length is 0 then it
    will not be truncated.'''
    if not text:
        return ''
    plain = RE_MD_HTML_TAGS.sub('', markdown(text))
    if not extract_length or len(plain) < extract_length:
        return literal(plain)

    return literal(
        text_type(
            whtext.truncate(
                plain,
                length=extract_length,
                indicator='...',
                whole_word=True
            )
        )
    )


@core_helper
def icon_url(name):
    return url_for_static('/images/icons/%s.png' % name)


@core_helper
def icon_html(url, alt=None, inline=True):
    classes = ''
    if inline:
        classes += 'inline-icon '
    return literal(('<img src="%s" height="16px" width="16px" alt="%s" ' +
                    'class="%s" /> ') % (url, alt, classes))


@core_helper
def icon(name, alt=None, inline=True):
    return icon_html(icon_url(name), alt, inline)


@core_helper
def resource_icon(res):
    if False:
        icon_name = 'page_white'
        # if (res.is_404?): icon_name = 'page_white_error'
        # also: 'page_white_gear'
        # also: 'page_white_link'
        return icon(icon_name)
    else:
        return icon(format_icon(res.get('format', '')))


@core_helper
def format_icon(_format):
    _format = _format.lower()
    if ('json' in _format):
        return 'page_white_cup'
    if ('csv' in _format):
        return 'page_white_gear'
    if ('xls' in _format):
        return 'page_white_excel'
    if ('zip' in _format):
        return 'page_white_compressed'
    if ('api' in _format):
        return 'page_white_database'
    if ('plain text' in _format):
        return 'page_white_text'
    if ('xml' in _format):
        return 'page_white_code'
    return 'page_white'


@core_helper
def dict_list_reduce(list_, key, unique=True):
    ''' Take a list of dicts and create a new one containing just the
    values for the key with unique values if requested. '''
    new_list = []
    for item in list_:
        value = item.get(key)
        if not value or (unique and value in new_list):
            continue
        new_list.append(value)
    return new_list


@core_helper
def linked_gravatar(email_hash, size=100, default=None):
    return literal(
        '<a href="https://gravatar.com/" target="_blank" ' +
        'title="%s" alt="">' % _('Update your avatar at gravatar.com') +
        '%s</a>' % gravatar(email_hash, size, default)
    )


_VALID_GRAVATAR_DEFAULTS = ['404', 'mm', 'identicon', 'monsterid',
                            'wavatar', 'retro']


@core_helper
def gravatar(email_hash, size=100, default=None):
    if default is None:
        default = config.get('ckan.gravatar_default', 'identicon')

    if default not in _VALID_GRAVATAR_DEFAULTS:
        # treat the default as a url
        default = urllib.quote(default, safe='')

    return literal('''<img src="//gravatar.com/avatar/%s?s=%d&amp;d=%s"
        class="gravatar" width="%s" height="%s" alt="Gravatar" />'''
                   % (email_hash, size, default, size, size)
                   )


@core_helper
def pager_url(page, partial=None, **kwargs):
    pargs = []
    if is_flask_request():
        pargs.append(request.endpoint)
        # FIXME: add `id` param to kwargs if it really required somewhere
    else:
        routes_dict = _pylons_default_url.environ['pylons.routes_dict']
        kwargs['controller'] = routes_dict['controller']
        kwargs['action'] = routes_dict['action']
        if routes_dict.get('id'):
            kwargs['id'] = routes_dict['id']
    kwargs['page'] = page
    return url_for(*pargs, **kwargs)


class Page(paginate.Page):
    # Curry the pager method of the webhelpers.paginate.Page class, so we have
    # our custom layout set as default.

    def pager(self, *args, **kwargs):
        kwargs.update(
            format=u"<div class='pagination-wrapper'><ul class='pagination'>"
            "$link_previous ~2~ $link_next</ul></div>",
            symbol_previous=u'«', symbol_next=u'»',
            curpage_attr={'class': 'active'}, link_attr={}
        )
        return super(Page, self).pager(*args, **kwargs)

    # Put each page link into a <li> (for Bootstrap to style it)

    def _pagerlink(self, page, text, extra_attributes=None):
        anchor = super(Page, self)._pagerlink(page, text)
        extra_attributes = extra_attributes or {}
        return HTML.li(anchor, **extra_attributes)

    # Change 'current page' link from <span> to <li><a>
    # and '..' into '<li><a>..'
    # (for Bootstrap to style them properly)

    def _range(self, regexp_match):
        html = super(Page, self)._range(regexp_match)
        # Convert ..
        dotdot = '<span class="pager_dotdot">..</span>'
        dotdot_link = HTML.li(HTML.a('...', href='#'), class_='disabled')
        html = re.sub(dotdot, dotdot_link, html)

        # Convert current page
        text = '%s' % self.page
        current_page_span = str(HTML.span(c=text, **self.curpage_attr))
        current_page_link = self._pagerlink(self.page, text,
                                            extra_attributes=self.curpage_attr)
        return re.sub(current_page_span, current_page_link, html)


@core_helper
def get_page_number(params, key='page', default=1):
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
def get_display_timezone():
    ''' Returns a pytz timezone for the display_timezone setting in the
    configuration file or UTC if not specified.
    :rtype: timezone
    '''
    timezone_name = config.get('ckan.display_timezone') or 'utc'

    if timezone_name == 'server':
        return tzlocal.get_localzone()

    return pytz.timezone(timezone_name)


@core_helper
def render_datetime(datetime_, date_format=None, with_hours=False):
    '''Render a datetime object or timestamp string as a localised date or
    in the requested format.
    If timestamp is badly formatted, then a blank string is returned.

    :param datetime_: the date
    :type datetime_: datetime or ISO string format
    :param date_format: a date format
    :type date_format: string
    :param with_hours: should the `hours:mins` be shown
    :type with_hours: bool

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
                                          with_hours=with_hours)


@core_helper
def date_str_to_datetime(date_str):
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

    time_tuple = re.split('[^\d]+', date_str, maxsplit=5)

    # Extract seconds and microseconds
    if len(time_tuple) >= 6:
        m = re.match('(?P<seconds>\d{2})(\.(?P<microseconds>\d{6}))?$',
                     time_tuple[5])
        if not m:
            raise ValueError('Unable to parse %s as seconds.microseconds' %
                             time_tuple[5])
        seconds = int(m.groupdict().get('seconds'))
        microseconds = int(m.groupdict(0).get('microseconds'))
        time_tuple = time_tuple[:5] + [seconds, microseconds]

    return datetime.datetime(*map(int, time_tuple))


@core_helper
def parse_rfc_2822_date(date_str, assume_utc=True):
    '''
    Parse a date string of the form specified in RFC 2822, and return a
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
        offset = 0 if time_tuple[-1] is None else time_tuple[-1]
        tz_info = _RFC2282TzInfo(offset)
    return datetime.datetime(*time_tuple[:6], microsecond=0, tzinfo=tz_info)


class _RFC2282TzInfo(datetime.tzinfo):
    '''
    A datetime.tzinfo implementation used by parse_rfc_2822_date() function.

    In order to return timezone information, a concrete implementation of
    datetime.tzinfo is required.  This class represents tzinfo that knows
    about it's offset from UTC, has no knowledge of daylight savings time, and
    no knowledge of the timezone name.

    '''

    def __init__(self, offset):
        '''
        offset from UTC in seconds.
        '''
        self.offset = datetime.timedelta(seconds=offset)

    def utcoffset(self, dt):
        return self.offset

    def dst(self, dt):
        '''
        Dates parsed from an RFC 2822 string conflate timezone and dst, and so
        it's not possible to determine whether we're in DST or not, hence
        returning None.
        '''
        return None

    def tzname(self, dt):
        return None


@core_helper
@maintain.deprecated('h.time_ago_in_words_from_str is deprecated in 2.2 '
                     'and will be removed.  Please use '
                     'h.time_ago_from_timestamp instead')
def time_ago_in_words_from_str(date_str, granularity='month'):
    '''Deprecated in 2.2 use time_ago_from_timestamp'''
    if date_str:
        return date.time_ago_in_words(date_str_to_datetime(date_str),
                                      granularity=granularity)
    else:
        return _('Unknown')


@core_helper
def time_ago_from_timestamp(timestamp):
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
def button_attr(enable, type='primary'):
    if enable:
        return 'class="btn %s"' % type
    return 'disabled class="btn disabled"'


@core_helper
def dataset_display_name(package_or_package_dict):
    if isinstance(package_or_package_dict, dict):
        return get_translated(package_or_package_dict, 'title') or \
            package_or_package_dict['name']
    else:
        # FIXME: we probably shouldn't use the same functions for
        # package dicts and real package objects
        return package_or_package_dict.title or package_or_package_dict.name


@core_helper
def dataset_link(package_or_package_dict):
    if isinstance(package_or_package_dict, dict):
        name = package_or_package_dict['name']
    else:
        name = package_or_package_dict.name
    text = dataset_display_name(package_or_package_dict)
    return tags.link_to(
        text,
        url_for(controller='package', action='read', id=name)
    )


@core_helper
def resource_display_name(resource_dict):
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
def resource_link(resource_dict, package_id):
    text = resource_display_name(resource_dict)
    url = url_for(controller='package',
                  action='resource_read',
                  id=package_id,
                  resource_id=resource_dict['id'])
    return tags.link_to(text, url)


@core_helper
def tag_link(tag):
    url = url_for(controller='tag', action='read', id=tag['name'])
    return tags.link_to(tag.get('title', tag['name']), url)


@core_helper
def group_link(group):
    url = url_for(controller='group', action='read', id=group['name'])
    return tags.link_to(group['title'], url)


@core_helper
def organization_link(organization):
    url = url_for(controller='organization', action='read',
                  id=organization['name'])
    return tags.link_to(organization['title'], url)


@core_helper
def dump_json(obj, **kw):
    return json.dumps(obj, **kw)


@core_helper
def auto_log_message():
    if (c.action == 'new'):
        return _('Created new dataset.')
    elif (c.action == 'editresources'):
        return _('Edited resources.')
    elif (c.action == 'edit'):
        return _('Edited settings.')
    return ''


@core_helper
def activity_div(template, activity, actor, object=None, target=None):
    actor = '<span class="actor">%s</span>' % actor
    if object:
        object = '<span class="object">%s</span>' % object
    if target:
        target = '<span class="target">%s</span>' % target
    rendered_datetime = render_datetime(activity['timestamp'])
    date = '<span class="date">%s</span>' % rendered_datetime
    template = template.format(actor=actor, date=date,
                               object=object, target=target)
    template = '<div class="activity">%s %s</div>' % (template, date)
    return literal(template)


@core_helper
def snippet(template_name, **kw):
    ''' This function is used to load html snippets into pages. keywords
    can be used to pass parameters into the snippet rendering '''
    import ckan.lib.base as base
    return base.render_snippet(template_name, **kw)


@core_helper
def convert_to_dict(object_type, objs):
    ''' This is a helper function for converting lists of objects into
    lists of dicts. It is for backwards compatability only. '''

    def dictize_revision_list(revision, context):
        # conversionof revision lists

        def process_names(items):
            array = []
            for item in items:
                array.append(item.name)
            return array

        rev = {'id': revision.id,
               'state': revision.state,
               'timestamp': revision.timestamp,
               'author': revision.author,
               'packages': process_names(revision.packages),
               'groups': process_names(revision.groups),
               'message': revision.message, }
        return rev
    import ckan.lib.dictization.model_dictize as md
    converters = {'package': md.package_dictize,
                  'revisions': dictize_revision_list}
    converter = converters[object_type]
    items = []
    context = {'model': model}
    for obj in objs:
        item = converter(obj, context)
        items.append(item)
    return items


# these are the types of objects that can be followed
_follow_objects = ['dataset', 'user', 'group']


@core_helper
def follow_button(obj_type, obj_id):
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
    if c.user:
        context = {'model': model, 'session': model.Session, 'user': c.user}
        action = 'am_following_%s' % obj_type
        following = logic.get_action(action)(context, {'id': obj_id})
        return snippet('snippets/follow_button.html',
                       following=following,
                       obj_id=obj_id,
                       obj_type=obj_type)
    return ''


@core_helper
def follow_count(obj_type, obj_id):
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
    context = {'model': model, 'session': model.Session, 'user': c.user}
    return logic.get_action(action)(context, {'id': obj_id})


def _create_url_with_params(params=None, controller=None, action=None,
                            extras=None):
    ''' internal function for building urls with parameters. '''

    if not controller:
        controller = c.controller
    if not action:
        action = c.action
    if not extras:
        extras = {}

    url = url_for(controller=controller, action=action, **extras)
    return _url_with_params(url, params)


@core_helper
def add_url_param(alternative_url=None, controller=None, action=None,
                  extras=None, new_params=None):
    '''
    Adds extra parameters to existing ones

    controller action & extras (dict) are used to create the base url via
    :py:func:`~ckan.lib.helpers.url_for` controller & action default to the
    current ones

    This can be overriden providing an alternative_url, which will be used
    instead.
    '''

    params_nopage = [(k, v) for k, v in request.params.items() if k != 'page']
    params = set(params_nopage)
    if new_params:
        params |= set(new_params.items())
    if alternative_url:
        return _url_with_params(alternative_url, params)
    return _create_url_with_params(params=params, controller=controller,
                                   action=action, extras=extras)


@core_helper
def remove_url_param(key, value=None, replace=None, controller=None,
                     action=None, extras=None, alternative_url=None):
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
    if isinstance(key, string_types):
        keys = [key]
    else:
        keys = key

    params_nopage = [(k, v) for k, v in request.params.items() if k != 'page']
    params = list(params_nopage)
    if value:
        params.remove((keys[0], value))
    else:
        for key in keys:
            [params.remove((k, v)) for (k, v) in params[:] if k == key]
    if replace is not None:
        params.append((keys[0], replace))

    if alternative_url:
        return _url_with_params(alternative_url, params)

    return _create_url_with_params(params=params, controller=controller,
                                   action=action, extras=extras)


@core_helper
def include_resource(resource):
    import ckan.lib.fanstatic_resources as fanstatic_resources
    r = getattr(fanstatic_resources, resource)
    r.need()


@core_helper
def urls_for_resource(resource):
    ''' Returns a list of urls for the resource specified.  If the resource
    is a group or has dependencies then there can be multiple urls.

    NOTE: This is for special situations only and is not the way to generally
    include resources.  It is advised not to use this function.'''
    import ckan.lib.fanstatic_resources as fanstatic_resources

    r = getattr(fanstatic_resources, resource)
    resources = list(r.resources)
    core = fanstatic_resources.fanstatic_extensions.core
    f = core.get_needed()
    lib = r.library
    root_path = f.library_url(lib)

    resources = core.sort_resources(resources)
    if f._bundle:
        resources = core.bundle_resources(resources)
    out = []
    for resource in resources:
        if isinstance(resource, core.Bundle):
            paths = [resource.relpath for resource in resource.resources()]
            relpath = ';'.join(paths)
            relpath = core.BUNDLE_PREFIX + relpath
        else:
            relpath = resource.relpath

        out.append('%s/%s' % (root_path, relpath))
    return out


@core_helper
def debug_inspect(arg):
    ''' Output pprint.pformat view of supplied arg '''
    return literal('<pre>') + pprint.pformat(arg) + literal('</pre>')


@core_helper
def popular(type_, number, min=1, title=None):
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
def groups_available(am_member=False):
    '''Return a list of the groups that the user is authorized to edit.

    :param am_member: if True return only the groups the logged-in user is a
      member of, otherwise return all groups that the user is authorized to
      edit (for example, sysadmin users are authorized to edit all groups)
      (optional, default: False)
    :type am-member: bool

    '''
    context = {}
    data_dict = {'available_only': True, 'am_member': am_member}
    return logic.get_action('group_list_authz')(context, data_dict)


@core_helper
def organizations_available(
        permission='manage_group', include_dataset_count=False):
    '''Return a list of organizations that the current user has the specified
    permission for.
    '''
    context = {'user': c.user}
    data_dict = {
        'permission': permission,
        'include_dataset_count': include_dataset_count}
    return logic.get_action('organization_list_for_user')(context, data_dict)


@core_helper
def roles_translated():
    '''Return a dict of available roles with their translations'''
    return authz.roles_trans()


@core_helper
def user_in_org_or_group(group_id):
    ''' Check if user is in a group or organization '''
    # we need a user
    if not c.userobj:
        return False
    # sysadmins can do anything
    if c.userobj.sysadmin:
        return True
    query = model.Session.query(model.Member) \
        .filter(model.Member.state == 'active') \
        .filter(model.Member.table_name == 'user') \
        .filter(model.Member.group_id == group_id) \
        .filter(model.Member.table_id == c.userobj.id)
    return len(query.all()) != 0


@core_helper
def dashboard_activity_stream(user_id, filter_type=None, filter_id=None,
                              offset=0):
    '''Return the dashboard activity stream of the current user.

    :param user_id: the id of the user
    :type user_id: string

    :param filter_type: the type of thing to filter by
    :type filter_type: string

    :param filter_id: the id of item to filter by
    :type filter_id: string

    :returns: an activity stream as an HTML snippet
    :rtype: string

    '''
    context = {'model': model, 'session': model.Session, 'user': c.user}

    if filter_type:
        action_functions = {
            'dataset': 'package_activity_list_html',
            'user': 'user_activity_list_html',
            'group': 'group_activity_list_html',
            'organization': 'organization_activity_list_html',
        }
        action_function = logic.get_action(action_functions.get(filter_type))
        return action_function(context, {'id': filter_id, 'offset': offset})
    else:
        return logic.get_action('dashboard_activity_list_html')(
            context, {'offset': offset})


@core_helper
def recently_changed_packages_activity_stream(limit=None):
    if limit:
        data_dict = {'limit': limit}
    else:
        data_dict = {}
    context = {'model': model, 'session': model.Session, 'user': c.user}
    return logic.get_action('recently_changed_packages_activity_list_html')(
        context, data_dict)


@core_helper
def escape_js(str_to_escape):
    '''Escapes special characters from a JS string.

       Useful e.g. when you need to pass JSON to the templates

       :param str_to_escape: string to be escaped
       :rtype: string
    '''
    return str_to_escape.replace('\\', '\\\\') \
        .replace('\'', '\\\'') \
        .replace('"', '\\\"')


@core_helper
def get_pkg_dict_extra(pkg_dict, key, default=None):
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
def get_request_param(parameter_name, default=None):
    ''' This function allows templates to access query string parameters
    from the request. This is useful for things like sort order in
    searches. '''
    return request.params.get(parameter_name, default)


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
    '[\w\-@?^=%&:\/~\\+#]'  # but last character can't be punctuation [.,;]
    ')',
    flags=re.UNICODE
)

# find all tags but ignore < in the strings so that we can use it correctly
# in markdown
RE_MD_HTML_TAGS = re.compile('<[^><]*>')


@core_helper
def html_auto_link(data):
    '''Linkifies HTML

    `tag` converted to a tag link

    `dataset` converted to a dataset link

    `group` converted to a group link

    `http://` converted to a link
    '''

    LINK_FNS = {
        'tag': tag_link,
        'group': group_link,
        'dataset': dataset_link,
        'package': dataset_link,
    }

    def makelink(matchobj):
        obj = matchobj.group(1)
        name = matchobj.group(2)
        title = '%s:%s' % (obj, name)
        return LINK_FNS[obj]({'name': name.strip('"'), 'title': title})

    def link(matchobj):
        return '<a href="%s" target="_blank" rel="nofollow">%s</a>' \
            % (matchobj.group(1), matchobj.group(1))

    def process(matchobj):
        data = matchobj.group(2)
        data = RE_MD_INTERNAL_LINK.sub(makelink, data)
        data = RE_MD_EXTERNAL_LINK.sub(link, data)
        return matchobj.group(1) + data

    data = RE_MD_GET_INNER_HTML.sub(process, data)
    return data


@core_helper
def render_markdown(data, auto_link=True, allow_html=False):
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
            tags=MARKDOWN_TAGS, attributes=MARKDOWN_ATTRIBUTES)
    # tags can be added by tag:... or tag:"...." and a link will be made
    # from it
    if auto_link:
        data = html_auto_link(data)
    return literal(data)


@core_helper
def format_resource_items(items):
    ''' Take a resource item list and format nicely with blacklisting etc. '''
    blacklist = ['name', 'description', 'url', 'tracking_summary']
    output = []
    # regular expressions for detecting types in strings
    reg_ex_datetime = '^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{6})?$'
    reg_ex_int = '^-?\d{1,}$'
    reg_ex_float = '^-?\d{1,}\.\d{1,}$'
    for key, value in items:
        if not value or key in blacklist:
            continue
        # size is treated specially as we want to show in MiB etc
        if key == 'size':
            try:
                value = formatters.localised_filesize(int(value))
            except ValueError:
                # Sometimes values that can't be converted to ints can sneak
                # into the db. In this case, just leave them as they are.
                pass
        elif isinstance(value, string_types):
            # check if strings are actually datetime/number etc
            if re.search(reg_ex_datetime, value):
                datetime_ = date_str_to_datetime(value)
                value = formatters.localised_nice_date(datetime_)
            elif re.search(reg_ex_float, value):
                value = formatters.localised_number(float(value))
            elif re.search(reg_ex_int, value):
                value = formatters.localised_number(int(value))
        elif ((isinstance(value, int) or isinstance(value, float))
                and value not in (True, False)):
            value = formatters.localised_number(value)
        key = key.replace('_', ' ')
        output.append((key, value))
    return sorted(output, key=lambda x: x[0])


@core_helper
def resource_preview(resource, package):
    '''
    Returns a rendered snippet for a embedded resource preview.

    Depending on the type, different previews are loaded.
    This could be an img tag where the image is loaded directly or an iframe
    that embeds a web page or a recline preview.
    '''

    if not resource['url']:
        return False

    datapreview.res_format(resource)
    directly = False
    data_dict = {'resource': resource, 'package': package}

    if datapreview.get_preview_plugin(data_dict, return_first=True):
        url = url_for(controller='package', action='resource_datapreview',
                      resource_id=resource['id'], id=package['id'],
                      qualified=True)
    else:
        return False

    return snippet("dataviewer/snippets/data_preview.html",
                   embed=directly,
                   resource_url=url,
                   raw_resource_url=resource.get('url'))


@core_helper
def get_allowed_view_types(resource, package):
    data_dict = {'resource': resource, 'package': package}
    plugins = datapreview.get_allowed_view_plugins(data_dict)

    allowed_view_types = []
    for plugin in plugins:
        info = plugin.info()
        allowed_view_types.append((info['name'],
                                   info.get('title', info['name']),
                                   info.get('icon', 'image')))
    allowed_view_types.sort(key=lambda item: item[1])
    return allowed_view_types


@core_helper
def rendered_resource_view(resource_view, resource, package, embed=False):
    '''
    Returns a rendered resource view snippet.
    '''
    view_plugin = datapreview.get_view_plugin(resource_view['view_type'])
    context = {}
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
def view_resource_url(resource_view, resource, package, **kw):
    '''
    Returns url for resource. made to be overridden by extensions. i.e
    by resource proxy.
    '''
    return resource['url']


@core_helper
def resource_view_is_filterable(resource_view):
    '''
    Returns True if the given resource view support filters.
    '''
    view_plugin = datapreview.get_view_plugin(resource_view['view_type'])
    return view_plugin.info().get('filterable', False)


@core_helper
def resource_view_get_fields(resource):
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
def resource_view_is_iframed(resource_view):
    '''
    Returns true if the given resource view should be displayed in an iframe.
    '''
    view_plugin = datapreview.get_view_plugin(resource_view['view_type'])
    return view_plugin.info().get('iframed', True)


@core_helper
def resource_view_icon(resource_view):
    '''
    Returns the icon for a particular view type.
    '''
    view_plugin = datapreview.get_view_plugin(resource_view['view_type'])
    return view_plugin.info().get('icon', 'picture')


@core_helper
def resource_view_display_preview(resource_view):
    '''
    Returns if the view should display a preview.
    '''
    view_plugin = datapreview.get_view_plugin(resource_view['view_type'])
    return view_plugin.info().get('preview_enabled', True)


@core_helper
def resource_view_full_page(resource_view):
    '''
    Returns if the edit view page should be full page.
    '''
    view_plugin = datapreview.get_view_plugin(resource_view['view_type'])
    return view_plugin.info().get('full_page_edit', False)


@core_helper
def remove_linebreaks(string):
    '''Remove linebreaks from string to make it usable in JavaScript'''
    return text_type(string).replace('\n', '')


@core_helper
def list_dict_filter(list_, search_field, output_field, value):
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
def SI_number_span(number):
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
localised_SI_number = formatters.localised_SI_number
localised_nice_date = formatters.localised_nice_date
localised_filesize = formatters.localised_filesize


@core_helper
def new_activities():
    '''Return the number of activities for the current user.

    See :func:`logic.action.get.dashboard_new_activities_count` for more
    details.

    '''
    if not c.userobj:
        return None
    action = logic.get_action('dashboard_new_activities_count')
    return action({}, {})


@core_helper
def uploads_enabled():
    if uploader.get_storage_path():
        return True
    return False


@core_helper
def get_featured_organizations(count=1):
    '''Returns a list of favourite organization in the form
    of organization_list action function
    '''
    config_orgs = config.get('ckan.featured_orgs', '').split()
    orgs = featured_group_org(get_action='organization_show',
                              list_action='organization_list',
                              count=count,
                              items=config_orgs)
    return orgs


@core_helper
def get_featured_groups(count=1):
    '''Returns a list of favourite group the form
    of organization_list action function
    '''
    config_groups = config.get('ckan.featured_groups', '').split()
    groups = featured_group_org(get_action='group_show',
                                list_action='group_list',
                                count=count,
                                items=config_groups)
    return groups


@core_helper
def featured_group_org(items, get_action, list_action, count):
    def get_group(id):
        context = {'ignore_auth': True,
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
def get_site_statistics():
    stats = {}
    stats['dataset_count'] = logic.get_action('package_search')(
        {}, {"rows": 1})['count']
    stats['group_count'] = len(logic.get_action('group_list')({}, {}))
    stats['organization_count'] = len(
        logic.get_action('organization_list')({}, {}))
    return stats


_RESOURCE_FORMATS = None


@core_helper
def resource_formats():
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
        _RESOURCE_FORMATS = {}
        format_file_path = config.get('ckan.resource_formats')
        if not format_file_path:
            format_file_path = os.path.join(
                os.path.dirname(os.path.realpath(ckan.config.__file__)),
                'resource_formats.json'
            )
        with open(format_file_path) as format_file:
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
def unified_resource_format(format):
    formats = resource_formats()
    format_clean = format.lower()
    if format_clean in formats:
        format_new = formats[format_clean][1]
    else:
        format_new = format
    return format_new


@core_helper
def check_config_permission(permission):
    return authz.check_config_permission(permission)


@core_helper
def get_organization(org=None, include_datasets=False):
    if org is None:
        return {}
    try:
        return logic.get_action('organization_show')(
            {}, {'id': org, 'include_datasets': include_datasets})
    except (logic.NotFound, logic.ValidationError, logic.NotAuthorized):
        return {}


@core_helper
def license_options(existing_license_id=None):
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
         register[license_id].title if license_id in register else license_id)
        for license_id in license_ids]


@core_helper
def get_translated(data_dict, field):
    language = i18n.get_lang()
    try:
        return data_dict[field + u'_translated'][language]
    except KeyError:
        val = data_dict.get(field, '')
        return _(val) if val and isinstance(val, string_types) else val


@core_helper
def facets():
    u'''Returns a list of the current facet names'''
    return config.get(u'search.facets', DEFAULT_FACET_NAMES).split()


@core_helper
def mail_to(email_address, name):
    email = escape(email_address)
    author = escape(name)
    html = Markup(u'<a href=mailto:{0}>{1}</a>'.format(email, author))
    return html


@core_helper
def radio(selected, id, checked):
    if checked:
        return literal((u'<input checked="checked" id="%s_%s" name="%s" \
            value="%s" type="radio">') % (selected, id, selected, id))
    return literal(('<input id="%s_%s" name="%s" \
        value="%s" type="radio">') % (selected, id, selected, id))


@core_helper
def clean_html(html):
    return bleach_clean(text_type(html))


core_helper(flash, name='flash')
core_helper(localised_number)
core_helper(localised_SI_number)
core_helper(localised_nice_date)
core_helper(localised_filesize)
# Useful additionsfrom the i18n library.
core_helper(i18n.get_available_locales)
core_helper(i18n.get_locales_dict)
# Useful additions from the webhelpers library.
core_helper(tags.literal)
core_helper(tags.link_to)
core_helper(tags.file)
core_helper(tags.submit)
core_helper(whtext.truncate)
# Useful additions from the paste library.
core_helper(converters.asbool)
# Useful additions from the stdlib.
core_helper(urlencode)


def load_plugin_helpers():
    """
    (Re)loads the list of helpers provided by plugins.
    """
    global helper_functions

    helper_functions.clear()
    helper_functions.update(_builtin_functions)

    for plugin in reversed(list(p.PluginImplementations(p.ITemplateHelpers))):
        helper_functions.update(plugin.get_helpers())


@core_helper
def sanitize_id(id_):
    '''Given an id (uuid4), if it has any invalid characters it raises
    ValueError.
    '''
    return str(uuid.UUID(id_))
