# coding=UTF-8

"""Helper functions

Consists of functions to typically be used within templates, but also
available to Controllers. This module is available to templates as 'h'.
"""
import email.utils
import datetime
import logging
import re
import urllib
import pprint
import copy
from urllib import urlencode

from paste.deploy.converters import asbool
from webhelpers.html import escape, HTML, literal, url_escape
from webhelpers.html.tools import mail_to
from webhelpers.html.tags import *
from webhelpers.markdown import markdown
from webhelpers import paginate
from webhelpers.text import truncate
import webhelpers.date as date
from pylons import url as _pylons_default_url
from pylons.decorators.cache import beaker_cache
from pylons import config
from routes import redirect_to as _redirect_to
from routes import url_for as _routes_default_url_for
from alphabet_paginate import AlphaPage
import i18n
import ckan.exceptions
from pylons import request
from pylons import session
from pylons import c, g
from pylons.i18n import _, ungettext

import ckan.lib.fanstatic_resources as fanstatic_resources
import ckan.model as model
import ckan.lib.formatters as formatters
import ckan.lib.maintain as maintain
import ckan.lib.datapreview as datapreview

get_available_locales = i18n.get_available_locales
get_locales_dict = i18n.get_locales_dict

log = logging.getLogger(__name__)

try:
    from collections import OrderedDict  # from python 2.7
except ImportError:
    from sqlalchemy.util import OrderedDict

try:
    import json
except ImportError:
    import simplejson as json

_log = logging.getLogger(__name__)


def redirect_to(*args, **kw):
    '''A routes.redirect_to wrapper to retain the i18n settings'''
    kw['__ckan_no_root'] = True
    if are_there_flash_messages():
        kw['__no_cache__'] = True
    return _redirect_to(url_for(*args, **kw))


def url(*args, **kw):
    """Create url adding i18n information if selected
    wrapper for pylons.url"""
    locale = kw.pop('locale', None)
    my_url = _pylons_default_url(*args, **kw)
    return _add_i18n_to_url(my_url, locale=locale, **kw)


def url_for(*args, **kw):
    """Create url adding i18n information if selected
    wrapper for routes.url_for"""
    locale = kw.pop('locale', None)
    # remove __ckan_no_root and add after to not pollute url
    no_root = kw.pop('__ckan_no_root', False)
    # routes will get the wrong url for APIs if the ver is not provided
    if kw.get('controller') == 'api':
        ver = kw.get('ver')
        if not ver:
            raise Exception('api calls must specify the version! e.g. ver=1')
        # fix ver to include the slash
        kw['ver'] = '/%s' % ver
    my_url = _routes_default_url_for(*args, **kw)
    kw['__ckan_no_root'] = no_root
    return _add_i18n_to_url(my_url, locale=locale, **kw)


def url_for_static(*args, **kw):
    """Create url for static content that does not get translated
    eg css, js
    wrapper for routes.url_for"""
    # make sure that if we specify the url that it is not unicode
    if args:
        args = (str(args[0]),) + args[1:]
    my_url = _routes_default_url_for(*args, **kw)
    return my_url


def _add_i18n_to_url(url_to_amend, **kw):
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
    try:
        root = request.environ.get('SCRIPT_NAME', '')
    except TypeError:
        root = ''
    if kw.get('qualified', False):
        # if qualified is given we want the full url ie http://...
        root = _routes_default_url_for('/', qualified=True)[:-1] + root
    # ckan.root_path is defined when we have none standard language
    # position in the url
    root_path = config.get('ckan.root_path', None)
    if root_path:
        # FIXME this can be written better once the merge
        # into the ecportal core is done - Toby
        # we have a special root specified so use that
        if default_locale:
            root = re.sub('/{{LANG}}', '', root_path)
        else:
            root = re.sub('{{LANG}}', locale, root_path)
        # make sure we don't have a trailing / on the root
        if root[-1] == '/':
            root = root[:-1]
        url = url_to_amend[len(re.sub('/{{LANG}}', '', root_path)):]
        url = '%s%s' % (root, url)
        root = re.sub('/{{LANG}}', '', root_path)
    else:
        if default_locale:
            url = url_to_amend
        else:
            # we need to strip the root from the url and the add it before
            # the language specification.
            url = url_to_amend[len(root):]
            url = '%s/%s%s' % (root, locale,  url)

    # stop the root being added twice in redirects
    if no_root:
        url = url_to_amend[len(root):]
        if not default_locale:
            url = '/%s%s' % (locale,  url)

    if url == '/packages':
        error = 'There is a broken url being created %s' % kw
        raise ckan.exceptions.CkanUrlException(error)

    return url


def full_current_url():
    ''' Returns the fully qualified current url (eg http://...) useful
    for sharing etc '''
    return(url_for(request.environ['CKAN_CURRENT_URL'], qualified=True))


def lang():
    ''' Return the language code for the current locale eg `en` '''
    return request.environ.get('CKAN_LANG')


def lang_native_name(lang=None):
    ''' Return the langage name currently used in it's localised form
        either from parameter or current environ setting'''
    lang = lang or lang()
    locale = get_locales_dict().get(lang)
    if locale:
        return locale.display_name or locale.english_name
    return lang


class Message(object):
    """A message returned by ``Flash.pop_messages()``.

    Converting the message to a string returns the message text. Instances
    also have the following attributes:

    * ``message``: the message text.
    * ``category``: the category specified when the message was created.
    """

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
                             % (self.default_category,))

    def __call__(self, message, category=None, ignore_duplicate=False,
                 allow_html=False):
        if not category:
            category = self.default_category
        elif self.categories and category not in self.categories:
            raise ValueError("unrecognized category %r" % (category,))
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
                    return    # Original message found, so exit early.
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


def flash_notice(message, allow_html=False):
    ''' Show a flash message of type notice '''
    flash(message, category='alert-info', allow_html=allow_html)


def flash_error(message, allow_html=False):
    ''' Show a flash message of type error '''
    flash(message, category='alert-error', allow_html=allow_html)


def flash_success(message, allow_html=False):
    ''' Show a flash message of type success '''
    flash(message, category='alert-success', allow_html=allow_html)


def are_there_flash_messages():
    ''' Returns True if there are flash messages for the current user '''
    return flash.are_there_messages()


def _link_active(kwargs):
    ''' creates classes for the link_to calls '''
    highlight_actions = kwargs.get('highlight_actions',
                                   kwargs.get('action', '')).split(' ')
    return (c.controller == kwargs.get('controller')
                and c.action in highlight_actions)


def _link_to(text, *args, **kwargs):
    '''Common link making code for several helper functions'''
    assert len(args)<2, 'Too many unnamed arguments'

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
            text = literal('<i class="icon-large icon-%s"></i> ' % icon) + text
        return text

    icon = kwargs.pop('icon', None)
    class_ = _link_class(kwargs)
    return link_to(
        _create_link_text(text, **kwargs),
        url_for(*args, **kwargs),
        class_=class_
    )


def nav_link(text, controller, **kwargs):
    '''
    params
    class_: pass extra class(s) to add to the <a> tag
    icon: name of ckan icon to use within the link
    condition: if False then no link is returned
    '''
    if kwargs.pop('condition', True):
        kwargs['controller'] = controller
        link = _link_to(text, **kwargs)
    else:
        link = ''
    return link


def nav_named_link(text, name, **kwargs):
    '''Create a link for a named route.'''
    return _link_to(text, name, **kwargs)


def subnav_link(text, action, **kwargs):
    '''Create a link for a named route.'''
    kwargs['action'] = action
    return _link_to(text, **kwargs)


@maintain.deprecated('h.subnav_named_route is deprecated please '
                     'use h.nav_named_link')
def subnav_named_route(text, routename, **kwargs):
    '''Generate a subnav element based on a named route
    Deprecated in ckan 2.0 '''
    return nav_named_link(text, routename, **kwargs)


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


def build_nav_icon(menu_item, title, **kw):
    ''' build a navigation item used for example in user/read_base.html

    outputs <li><a href="..."><i class="icon.."></i> title</a></li>

    :param menu_item: the name of the defined menu item defined in
    config/routing as the named route of the same name
    :type menu_item: string
    :param title: text used for the link
    :type title: string
    :param **kw: additional keywords needed for creating url eg id=...

    :rtype: HTML literal
    '''
    return _make_menu_item(menu_item, title, **kw)


def build_nav(menu_item, title, **kw):
    ''' build a navigation item used for example breadcrumbs

    outputs <li><a href="..."></i> title</a></li>

    :param menu_item: the name of the defined menu item defined in
    config/routing as the named route of the same name
    :type menu_item: string
    :param title: text used for the link
    :type title: string
    :param **kw: additional keywords needed for creating url eg id=...

    :rtype: HTML literal
    '''
    return _make_menu_item(menu_item, title, icon=None, **kw)


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
    _menu_items = config['routes.named_routes']
    if menu_item not in _menu_items:
        raise Exception('menu item `%s` cannot be found' % menu_item)
    item = copy.copy(_menu_items[menu_item])
    item.update(kw)
    active =  _link_active(item)
    controller = item.pop('controller')
    needed = item.pop('needed')
    for need in needed:
        if need not in kw:
            raise Exception('menu item `%s` need parameter `%s`'
                            % (menu_item, need))
    link = nav_link(title, controller, suppress_active_class=True, **item)
    if active:
        return literal('<li class="active">') + link + literal('</li>')
    return literal('<li>') + link + literal('</li>')


def default_group_type():
    return str(config.get('ckan.default.group_type', 'group'))


def get_facet_items_dict(facet, limit=10, exclude_active=False):
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
    if not c.search_facets or \
       not c.search_facets.get(facet) or \
       not c.search_facets.get(facet).get('items'):
        return []
    facets = []
    for facet_item in c.search_facets.get(facet)['items']:
        if not len(facet_item['name'].strip()):
            continue
        if not (facet, facet_item['name']) in request.params.items():
            facets.append(dict(active=False, **facet_item))
        elif not exclude_active:
            facets.append(dict(active=True, **facet_item))
    facets = sorted(facets, key=lambda item: item['count'], reverse=True)
    if c.search_facets_limits:
        limit = c.search_facets_limits.get(facet)
    if limit:
        return facets[:limit]
    else:
        return facets


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


def get_facet_title(name):

    # if this is set in the config use this
    config_title = config.get('search.facets.%s.title' % name)
    if config_title:
        return config_title

    facet_titles = {'groups': _('Groups'),
                  'tags': _('Tags'),
                  'res_format': _('Formats'),
                  'license': _('Licence'), }
    return facet_titles.get(name, name.capitalize())


def get_param_int(name, default=10):
    return int(request.params.get(name, default))


def _url_with_params(url, params):
    if not params:
        return url
    params = [(k, v.encode('utf-8') if isinstance(v, basestring) else str(v)) \
                                  for k, v in params]
    return url + u'?' + urlencode(params)


def _search_url(params):
    url = url_for(controller='package', action='search')
    return _url_with_params(url, params)


def sorted_extras(list_):
    ''' Used for outputting package extras '''
    output = []
    for extra in sorted(list_, key=lambda x: x['key']):
        if extra.get('state') == 'deleted':
            continue
        k, v = extra['key'], extra['value']
        if k in g.package_hide_extras:
            continue
        if isinstance(v, (list, tuple)):
            v = ", ".join(map(unicode, v))
        output.append((k, v))
    return output


def check_access(action, data_dict=None):
    from ckan.logic import check_access as check_access_logic, NotAuthorized

    context = {'model': model,
                'user': c.user or c.author}
    if not data_dict:
        data_dict = {}

    try:
        check_access_logic(action, context, data_dict)
        authorized = True
    except NotAuthorized:
        authorized = False

    return authorized


def linked_user(user, maxlength=0, avatar=20):
    if user in [model.PSEUDO_USER__LOGGED_IN, model.PSEUDO_USER__VISITOR]:
        return user
    if not isinstance(user, model.User):
        user_name = unicode(user)
        user = model.User.get(user_name)
        if not user:
            return user_name
    if user:
        name = user.name if model.User.VALID_NAME.match(user.name) else user.id
        icon = gravatar(email_hash=user.email_hash, size=avatar)
        displayname = user.display_name
        if maxlength and len(user.display_name) > maxlength:
            displayname = displayname[:maxlength] + '...'
        return icon + u' ' + link_to(displayname,
                       url_for(controller='user', action='read', id=name))


def group_name_to_title(name):
    group = model.Group.by_name(name)
    if group is not None:
        return group.display_name
    return name


def markdown_extract(text, extract_length=190):
    ''' return the plain text representation of markdown encoded text.  That
    is the texted without any html tags.  If extract_length is 0 then it
    will not be truncated.'''
    if (text is None) or (text.strip() == ''):
        return ''
    plain = re.sub(r'<.*?>', '', markdown(text))
    if not extract_length or len(plain) < extract_length:
        return plain
    return literal(unicode(truncate(plain, length=extract_length, indicator='...', whole_word=True)))


def icon_url(name):
    return url_for_static('/images/icons/%s.png' % name)


def icon_html(url, alt=None, inline=True):
    classes = ''
    if inline:
        classes += 'inline-icon '
    return literal(('<img src="%s" height="16px" width="16px" alt="%s" ' +
                    'class="%s" /> ') % (url, alt, classes))


def icon(name, alt=None, inline=True):
    return icon_html(icon_url(name), alt, inline)


def resource_icon(res):
    if False:
        icon_name = 'page_white'
    # if (res.is_404?): icon_name = 'page_white_error'
    # also: 'page_white_gear'
    # also: 'page_white_link'
        return icon(icon_name)
    else:
        return icon(format_icon(res.get('format', '')))


def format_icon(_format):
    _format = _format.lower()
    if ('json' in _format): return 'page_white_cup'
    if ('csv' in _format): return 'page_white_gear'
    if ('xls' in _format): return 'page_white_excel'
    if ('zip' in _format): return 'page_white_compressed'
    if ('api' in _format): return 'page_white_database'
    if ('plain text' in _format): return 'page_white_text'
    if ('xml' in _format): return 'page_white_code'
    return 'page_white'


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


def linked_gravatar(email_hash, size=100, default=None):
    return literal(
        '<a href="https://gravatar.com/" target="_blank" ' +
        'title="%s">' % _('Update your avatar at gravatar.com') +
        '%s</a>' % gravatar(email_hash, size, default)
        )

_VALID_GRAVATAR_DEFAULTS = ['404', 'mm', 'identicon', 'monsterid',
                            'wavatar', 'retro']


def gravatar(email_hash, size=100, default=None):
    if default is None:
        default = config.get('ckan.gravatar_default', 'identicon')

    if not default in _VALID_GRAVATAR_DEFAULTS:
        # treat the default as a url
        default = urllib.quote(default, safe='')

    return literal('''<img src="http://gravatar.com/avatar/%s?s=%d&amp;d=%s"
        class="gravatar" width="%s" height="%s" />'''
        % (email_hash, size, default, size, size)
        )


def pager_url(page, partial=None, **kwargs):
    routes_dict = _pylons_default_url.environ['pylons.routes_dict']
    kwargs['controller'] = routes_dict['controller']
    kwargs['action'] = routes_dict['action']
    if routes_dict.get('id'):
        kwargs['id'] = routes_dict['id']
    kwargs['page'] = page
    return url(**kwargs)


class Page(paginate.Page):
    # Curry the pager method of the webhelpers.paginate.Page class, so we have
    # our custom layout set as default.

    def pager(self, *args, **kwargs):
        kwargs.update(
            format=u"<div class='pagination pagination-centered'><ul>$link_previous ~2~ $link_next</ul></div>",
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


def render_datetime(datetime_, date_format=None, with_hours=False):
    '''Render a datetime object or timestamp string as a pretty string
    (Y-m-d H:m).
    If timestamp is badly formatted, then a blank string is returned.
    '''
    if not date_format:
        date_format = '%b %d, %Y'
        if with_hours:
            date_format += ', %H:%M'
    if isinstance(datetime_, datetime.datetime):
        return datetime_.strftime(date_format)
    elif isinstance(datetime_, basestring):
        try:
            datetime_ = date_str_to_datetime(datetime_)
        except TypeError:
            return ''
        except ValueError:
            return ''
        return datetime_.strftime(date_format)
    else:
        return ''


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


def parse_rfc_2822_date(date_str, assume_utc=True):
    """
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
    """
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
    """
    A datetime.tzinfo implementation used by parse_rfc_2822_date() function.

    In order to return timezone information, a concrete implementation of
    datetime.tzinfo is required.  This class represents tzinfo that knows
    about it's offset from UTC, has no knowledge of daylight savings time, and
    no knowledge of the timezone name.

    """

    def __init__(self, offset):
        """
        offset from UTC in seconds.
        """
        self.offset = datetime.timedelta(seconds=offset)

    def utcoffset(self, dt):
        return self.offset

    def dst(self, dt):
        """
        Dates parsed from an RFC 2822 string conflate timezone and dst, and so
        it's not possible to determine whether we're in DST or not, hence
        returning None.
        """
        return None

    def tzname(self, dt):
        return None


def time_ago_in_words_from_str(date_str, granularity='month'):
    if date_str:
        return date.time_ago_in_words(date_str_to_datetime(date_str),
                                      granularity=granularity)
    else:
        return _('Unknown')


def button_attr(enable, type='primary'):
    if enable:
        return 'class="btn %s"' % type
    return 'disabled class="btn disabled"'


def dataset_display_name(package_or_package_dict):
    if isinstance(package_or_package_dict, dict):
        return package_or_package_dict.get('title', '') or \
               package_or_package_dict.get('name', '')
    else:
        return package_or_package_dict.title or package_or_package_dict.name


def dataset_link(package_or_package_dict):
    if isinstance(package_or_package_dict, dict):
        name = package_or_package_dict['name']
    else:
        name = package_or_package_dict.name
    text = dataset_display_name(package_or_package_dict)
    return link_to(
        text,
        url_for(controller='package', action='read', id=name)
        )


# TODO: (?) support resource objects as well
def resource_display_name(resource_dict):
    name = resource_dict.get('name', None)
    description = resource_dict.get('description', None)
    url = resource_dict.get('url')
    if name:
        return name
    elif description:
        description = description.split('.')[0]
        max_len = 60
        if len(description) > max_len:
            description = description[:max_len] + '...'
        return description
    elif url:
        return url
    else:
        noname_string = _('no name')
        return '[%s] %s' % (noname_string, resource_dict['id'])


def resource_link(resource_dict, package_id):
    text = resource_display_name(resource_dict)
    url = url_for(controller='package',
        action='resource_read',
        id=package_id,
        resource_id=resource_dict['id'])
    return link_to(text, url)


def related_item_link(related_item_dict):
    text = related_item_dict.get('title', '')
    url = url_for(controller='related',
        action='read',
        id=related_item_dict['id'])
    return link_to(text, url)


def tag_link(tag):
    url = url_for(controller='tag', action='read', id=tag['name'])
    return link_to(tag['name'], url)


def group_link(group):
    url = url_for(controller='group', action='read', id=group['name'])
    return link_to(group['title'], url)


def organization_link(organization):
    url = url_for(controller='organization', action='read', id=organization['name'])
    return link_to(organization['name'], url)


def dump_json(obj, **kw):
    return json.dumps(obj, **kw)


def _get_template_name():
    #FIX ME THIS IS BROKEN
    ''' helper function to get the currently/last rendered template name '''
    return c.__debug_info[-1]['template_name']


def auto_log_message():
    if (c.action == 'new'):
        return _('Created new dataset.')
    elif (c.action == 'editresources'):
        return _('Edited resources.')
    elif (c.action == 'edit'):
        return _('Edited settings.')
    return ''


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


def snippet(template_name, **kw):
    ''' This function is used to load html snippets into pages. keywords
    can be used to pass parameters into the snippet rendering '''
    import ckan.lib.base as base
    return base.render_snippet(template_name, **kw)


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
    import lib.dictization.model_dictize as md
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
    import ckan.logic as logic
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


def follow_count(obj_type, obj_id):
    '''Return the number of followers of an object.

    :param obj_type: the type of the object, e.g. 'user' or 'dataset'
    :type obj_type: string
    :param obj_id: the id of the object
    :type obj_id: string

    :returns: the number of followers of the object
    :rtype: int

    '''
    import ckan.logic as logic
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

def add_url_param(alternative_url=None, controller=None, action=None,
                   extras=None, new_params=None):
    '''
    Adds extra parameters to existing ones

    controller action & extras (dict) are used to create the base url
    via url_for(controller=controller, action=action, **extras)
    controller & action default to the current ones

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


def remove_url_param(key, value=None, replace=None, controller=None,
                     action=None, extras=None, alternative_url=None):
    ''' Remove a key from the current parameters. A specific key/value
    pair can be removed by passing a second value argument otherwise all
    pairs matching the key will be removed. If replace is given then a
    new param key=replace will be added.

    controller action & extras (dict) are used to create the base url
    via url_for(controller=controller, action=action, **extras)
    controller & action default to the current ones

    This can be overriden providing an alternative_url, which will be used
    instead.
    '''
    params_nopage = [(k, v) for k, v in request.params.items() if k != 'page']
    params = list(params_nopage)
    if value:
        params.remove((key, value))
    else:
        [params.remove((k, v)) for (k, v) in params[:] if k == key]
    if replace is not None:
        params.append((key, replace))

    if alternative_url:
        return _url_with_params(alternative_url, params)

    return _create_url_with_params(params=params, controller=controller,
                                   action=action, extras=extras)


def include_resource(resource):
    r = getattr(fanstatic_resources, resource)
    r.need()


def urls_for_resource(resource):
    ''' Returns a list of urls for the resource specified.  If the resource
    is a group or has dependencies then there can be multiple urls.

    NOTE: This is for special situations only and is not the way to generally
    include resources.  It is advised not to use this function.'''
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


def debug_inspect(arg):
    ''' Output pprint.pformat view of supplied arg '''
    return literal('<pre>') + pprint.pformat(arg) + literal('</pre>')


def debug_full_info_as_list(debug_info):
    ''' This dumps the template variables for debugging purposes only. '''
    out = []
    ignored_keys = ['c', 'app_globals', 'g', 'h', 'request', 'tmpl_context',
                    'actions', 'translator', 'session', 'N_', 'ungettext',
                    'config', 'response', '_']
    ignored_context_keys = ['__class__', '__context', '__delattr__', '__dict__',
                            '__doc__', '__format__', '__getattr__',
                            '__getattribute__', '__hash__', '__init__',
                            '__module__', '__new__', '__reduce__',
                            '__reduce_ex__', '__repr__', '__setattr__',
                            '__sizeof__', '__str__', '__subclasshook__',
                            '__weakref__', 'action', 'environ', 'pylons',
                            'start_response']
    debug_vars = debug_info['vars']
    for key in debug_vars.keys():
        if not key in ignored_keys:
            data = pprint.pformat(debug_vars.get(key))
            data = data.decode('utf-8')
            out.append((key, data))

    if 'tmpl_context' in debug_vars:
        for key in debug_info['c_vars']:

            if not key in ignored_context_keys:
                data = pprint.pformat(getattr(debug_vars['tmpl_context'], key))
                data = data.decode('utf-8')
                out.append(('c.%s' % key, data))

    return out


def popular(type_, number, min=1, title=None):
    ''' display a popular icon. '''
    if type_ == 'views':
        title = ungettext('{number} view', '{number} views', number)
    elif type_ == 'recent views':
        title = ungettext('{number} recent view', '{number} recent views', number)
    elif not title:
        raise Exception('popular() did not recieve a valid type_ or title')
    return snippet('snippets/popular.html', title=title, number=number, min=min)


def groups_available():
    ''' return a list of available groups '''
    import ckan.logic as logic
    context = {'model': model, 'session': model.Session,
               'user': c.user or c.author}
    data_dict = {'available_only': True}
    return logic.get_action('group_list_authz')(context, data_dict)


def organizations_available(permission='edit_group'):
    ''' return a list of available organizations '''
    import ckan.logic as logic
    context = {'model': model, 'session': model.Session,
               'user': c.user}
    data_dict = {'permission': permission}
    return logic.get_action('organization_list_for_user')(context, data_dict)


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


def dashboard_activity_stream(user_id, offset=0):
    '''Return the dashboard activity stream of the given user.

    :param user_id: the id of the user
    :type user_id: string

    :returns: an activity stream as an HTML snippet
    :rtype: string

    '''
    import ckan.logic as logic
    context = {'model': model, 'session': model.Session, 'user': c.user}
    return logic.get_action('dashboard_activity_list_html')(context,
                                                            {'id': user_id,
                                                             'offset': offset})


def recently_changed_packages_activity_stream():
    import ckan.logic as logic
    context = {'model': model, 'session': model.Session, 'user': c.user}
    return logic.get_action('recently_changed_packages_activity_list_html')(
            context, {})


def escape_js(str_to_escape):
    '''Escapes special characters from a JS string.

       Useful e.g. when you need to pass JSON to the templates

       :param str_to_escape: string to be escaped
       :rtype: string
    '''
    return str_to_escape.replace('\\', '\\\\') \
                        .replace('\'', '\\\'') \
                        .replace('"', '\\\"')


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


def get_request_param(parameter_name, default=None):
    ''' This function allows templates to access query string parameters
    from the request. This is useful for things like sort order in
    searches. '''
    return request.params.get(parameter_name, default)


def render_markdown(data):
    ''' returns the data as rendered markdown '''
    # cope with data == None
    if not data:
        return ''
    return literal(ckan.misc.MarkdownFormat().to_html(data))


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
            value = formatters.localised_filesize(int(value))
        elif isinstance(value, basestring):
            # check if strings are actually datetime/number etc
            if re.search(reg_ex_datetime, value):
                datetime_ = date_str_to_datetime(value)
                value = formatters.localised_nice_date(datetime_)
            elif re.search(reg_ex_float, value):
                value = formatters.localised_number(float(value))
            elif re.search(reg_ex_int, value):
                value = formatters.localised_number(int(value))
        elif isinstance(value, int) or isinstance(value, float):
            value = formatters.localised_number(value)
        key = key.replace('_', ' ')
        output.append((key, value))
    return sorted(output, key=lambda x: x[0])


def resource_preview(resource, pkg_id):
    '''
    Returns a rendered snippet for a embedded resource preview.

    Depending on the type, different previews are loaded.
    This could be an img tag where the image is loaded directly or an iframe that
    embeds a web page, recline or a pdf preview.
    '''

    format_lower = resource['format'].lower()
    directly = False
    url = ''

    data_dict = {'resource': resource, 'package': c.package}

    if not resource['url']:
        log.info('No url for resource {0} defined.'.format(resource['id']))
        return snippet(
            "dataviewer/snippets/no_preview.html",
            resource_type=format_lower,
            reason='No valid resource url has been defined.'
            )
    direct_embed = config.get('ckan.preview.direct', '').split()
    if not direct_embed:
        direct_embed = datapreview.DEFAULT_DIRECT_EMBED
    loadable_in_iframe = config.get('ckan.preview.loadable', '').split()
    if not loadable_in_iframe:
        loadable_in_iframe = datapreview.DEFAULT_LOADABLE_IFRAME

    if datapreview.can_be_previewed(data_dict):
        url = url_for(controller='package', action='resource_datapreview',
            resource_id=resource['id'], id=pkg_id, qualified=True)
    elif format_lower in direct_embed:
        directly = True
        url = resource['url']
    elif format_lower in loadable_in_iframe:
        url = resource['url']
    else:
        log.info('No preview handler for resource type {0}'.format(format_lower))
        return snippet(
            "dataviewer/snippets/no_preview.html",
            resource_type=format_lower
            )

    return snippet(
        "dataviewer/snippets/data_preview.html",
        embed=directly,
        resource_url=url
        )


def SI_number_span(number):
    ''' outputs a span with the number in SI unit eg 14700 -> 14.7k '''
    number = int(number)
    if number < 1000:
        output = literal('<span>')
    else:
        output = literal('<span title="' + formatters.localised_number(number) + '">')
    return output + formatters.localised_SI_number(number) + literal('<span>')


# these are the functions that will end up in `h` template helpers
__allowed_functions__ = [
    # functions defined in ckan.lib.helpers
           'redirect_to',
           'url',
           'url_for',
           'url_for_static',
           'lang',
           'flash',
           'flash_error',
           'flash_notice',
           'flash_success',
           'nav_link',
           'nav_named_link',
           'subnav_link',
           'subnav_named_route',
           'default_group_type',
           'check_access',
           'linked_user',
           'group_name_to_title',
           'markdown_extract',
           'icon',
           'icon_html',
           'icon_url',
           'resource_icon',
           'format_icon',
           'linked_gravatar',
           'gravatar',
           'pager_url',
           'render_datetime',
           'date_str_to_datetime',
           'parse_rfc_2822_date',
           'time_ago_in_words_from_str',
           'button_attr',
           'dataset_display_name',
           'dataset_link',
           'resource_display_name',
           'resource_link',
           'related_item_link',
           'tag_link',
           'group_link',
           'dump_json',
           'auto_log_message',
           'snippet',
           'convert_to_dict',
           'activity_div',
           'lang_native_name',
           'get_facet_items_dict',
           'unselected_facet_items',
           'include_resource',
           'urls_for_resource',
           'build_nav_main',
           'build_nav_icon',
           'build_nav',
           'debug_inspect',
           'dict_list_reduce',
           'full_current_url',
           'popular',
           'debug_full_info_as_list',
           'get_facet_title',
           'get_param_int',
           'sorted_extras',
           'follow_button',
           'follow_count',
           'remove_url_param',
           'add_url_param',
           'groups_available',
           'organizations_available',
           'user_in_org_or_group',
           'dashboard_activity_stream',
           'recently_changed_packages_activity_stream',
           'escape_js',
           'get_pkg_dict_extra',
           'get_request_param',
           'render_markdown',
           'format_resource_items',
           'resource_preview',
           'SI_number_span',
           # imported into ckan.lib.helpers
           'literal',
           'link_to',
           'get_available_locales',
           'get_locales_dict',
           'truncate',
           'file',
           'mail_to',
           'radio',
           'submit',
           'asbool',
]
