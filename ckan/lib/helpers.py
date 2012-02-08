# coding=UTF-8

"""Helper functions

Consists of functions to typically be used within templates, but also
available to Controllers. This module is available to templates as 'h'.
"""
import datetime
import re

from webhelpers.html import escape, HTML, literal, url_escape
from webhelpers.html.tools import mail_to
from webhelpers.html.tags import *
from webhelpers.markdown import markdown
from webhelpers import paginate
from webhelpers.text import truncate
import webhelpers.date as date
from pylons import url
from pylons.decorators.cache import beaker_cache
from routes import url_for, redirect_to
from alphabet_paginate import AlphaPage
from lxml.html import fromstring
from i18n import get_available_locales



try:
    from collections import OrderedDict # from python 2.7
except ImportError:
    from sqlalchemy.util import OrderedDict

try:
    import json
except ImportError:
    import simplejson as json
    

class Message(object):
    """A message returned by ``Flash.pop_messages()``.

    Converting the message to a string returns the message text. Instances
    also have the following attributes:

    * ``message``: the message text.
    * ``category``: the category specified when the message was created.
    """

    def __init__(self, category, message, allow_html):
        self.category=category
        self.message=message
        self.allow_html=allow_html

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
    categories = ["warning", "notice", "error", "success"]
    
    # Default category if none is specified.
    default_category = "notice"

    def __init__(self, session_key="flash", categories=None, default_category=None):
        self.session_key = session_key
        if categories is not None:
            self.categories = categories
        if default_category is not None:
            self.default_category = default_category
        if self.categories and self.default_category not in self.categories:
            raise ValueError("unrecognized default category %r" % (self.default_category,))

    def __call__(self, message, category=None, ignore_duplicate=False, allow_html=False):
        if not category:
            category = self.default_category
        elif self.categories and category not in self.categories:
            raise ValueError("unrecognized category %r" % (category,))
        # Don't store Message objects in the session, to avoid unpickling
        # errors in edge cases.
        new_message_tuple = (category, message, allow_html)
        from pylons import session
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
        from pylons import session
        messages = session.pop(self.session_key, [])
        session.save()
        return [Message(*m) for m in messages]

    def are_there_messages(self):
        from pylons import session
        return bool(session.get(self.session_key))

_flash = _Flash()

def flash_notice(message, allow_html=False): 
    _flash(message, category='notice', allow_html=allow_html)

def flash_error(message, allow_html=False): 
    _flash(message, category='error', allow_html=allow_html)

def flash_success(message, allow_html=False): 
    _flash(message, category='success', allow_html=allow_html)

def are_there_flash_messages():
    return _flash.are_there_messages()

# FIXME: shouldn't have to pass the c object in to this.
def nav_link(c, text, controller, **kwargs):
    highlight_actions = kwargs.pop("highlight_actions", 
                                   kwargs["action"]).split()
    return link_to(
        text,
        url_for(controller=controller, **kwargs),
        class_=('active' if 
                c.controller == controller and c.action in highlight_actions
                else '')
    )

# FIXME: shouldn't have to pass the c object in to this.
def subnav_link(c, text, action, **kwargs):
    return link_to(
        text, 
        url_for(action=action, **kwargs),
        class_=('active' if c.action == action else '')
    )
    
def subnav_named_route(c, text, routename,**kwargs):
    """ Generate a subnav element based on a named route """
    return link_to(
        text, 
        url_for(routename, **kwargs),
        class_=('active' if c.action == kwargs['action'] else '')
    )    

def facet_items(c, name, limit=10):
    from pylons import request
    if not c.facets or not c.facets.get(name): 
        return []
    facets = []
    for k, v in c.facets.get(name).items():
        if not len(k.strip()):
            continue
        if not (name, k) in request.params.items():
            facets.append((k, v))
    return sorted(facets, key=lambda (k, v): v, reverse=True)[:limit]

def facet_title(name):
    from pylons import config 
    return config.get('search.facets.%s.title' % name, name.capitalize())

def am_authorized(c, action, domain_object=None):
    ''' Deprecated. Please use check_access instead'''
    from ckan.authz import Authorizer
    if domain_object is None:
        from ckan import model
        domain_object = model.System()
    return Authorizer.am_authorized(c, action, domain_object)

def check_access(action,data_dict=None):
    from ckan import model
    from ckan.lib.base import c
    from ckan.logic import check_access as check_access_logic,NotAuthorized

    context = {'model': model,
                'user': c.user or c.author}

    try:
        check_access_logic(action,context,data_dict)
        authorized = True
    except NotAuthorized:
        authorized = False

    return authorized

def linked_user(user, maxlength=0):
    from ckan import model
    from urllib import quote
    if user in [model.PSEUDO_USER__LOGGED_IN, model.PSEUDO_USER__VISITOR]:
        return user
    if not isinstance(user, model.User):
        user_name = unicode(user)
        user = model.User.get(user_name)
        if not user:
            return user_name
    if user:
        _name = user.name if model.User.VALID_NAME.match(user.name) else user.id
        _icon = gravatar(user.email_hash, 20)
        displayname = user.display_name
        if maxlength and len(user.display_name) > maxlength:
            displayname = displayname[:maxlength] + '...'
        return _icon + link_to(displayname, 
                       url_for(controller='user', action='read', id=_name))

def linked_authorization_group(authgroup, maxlength=0):
    from ckan import model
    from urllib import quote
    if not isinstance(authgroup, model.AuthorizationGroup):
        authgroup_name = unicode(authgroup)
        authgroup = model.AuthorizationGroup.get(authgroup_name)
        if not authgroup:
            return authgroup_name
    if authgroup:
        displayname = authgroup.name or authgroup.id
        if maxlength and len(display_name) > maxlength:
            displayname = displayname[:maxlength] + '...'
        return link_to(displayname, 
                       url_for(controller='authorization_group', action='read', id=displayname))

def group_name_to_title(name):
    from ckan import model
    group = model.Group.by_name(name)
    if group is not None:
        return group.display_name
    return name

def markdown_extract(text, extract_length=190):
    if (text is None) or (text.strip() == ''):
        return ''
    html = fromstring(markdown(text))
    plain = html.xpath("string()")
    return unicode(truncate(plain, length=extract_length, indicator='...', whole_word=True))

def icon_url(name):
    return url_for('/images/icons/%s.png' % name)

def icon_html(url, alt=None):
    return literal('<img src="%s" height="16px" width="16px" alt="%s" /> ' % (url, alt))

def icon(name, alt=None):
    return icon_html(icon_url(name),alt)

def linked_gravatar(email_hash, size=100, default="identicon"):
    return literal('''<a href="https://gravatar.com/" target="_blank"
        title="Update your avatar at gravatar.com">
        %s</a>''' %
            gravatar(email_hash,size,default)
        )

def gravatar(email_hash, size=100, default="identicon"):
    return literal('''<img src="http://gravatar.com/avatar/%s?s=%d&amp;d=%s"
        class="gravatar" />'''
        % (email_hash, size, default)
        )

def pager_url(page, partial=None, **kwargs):
    routes_dict = url.environ['pylons.routes_dict']
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
            format=u"<div class='pager'>$link_previous ~2~ $link_next</div>",
            symbol_previous=u'« Prev', symbol_next=u'Next »'
        )
        return super(Page, self).pager(*args, **kwargs)

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

def datetime_to_date_str(datetime_):
    '''Takes a datetime.datetime object and returns a string of it
    in ISO format.
    '''
    return datetime_.isoformat()

def date_str_to_datetime(date_str):
    '''Takes an ISO format timestamp and returns the equivalent
    datetime.datetime object.
    '''
    # Doing this split is more accepting of input variations than doing
    # a strptime. Also avoids problem with Python 2.5 not having %f.
    return datetime.datetime(*map(int, re.split('[^\d]', date_str)))

def time_ago_in_words_from_str(date_str, granularity='month'):
    if date_str:
        return date.time_ago_in_words(date_str_to_datetime(date_str), granularity=granularity)
    else:
        return 'Unknown'

def button_attr(enable, type='primary'):
    if enable:
        return 'class="pretty-button %s"' % type
    return 'disabled class="pretty-button disabled"'

def dataset_display_name(package_or_package_dict):
    if isinstance(package_or_package_dict, dict):
        return package_or_package_dict.get('title', '') or package_or_package_dict.get('name', '')
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
    if name:
        return name
    elif description:
        description = description.split('.')[0]
        max_len = 60;
        if len(description)>max_len: description = description[:max_len]+'...'
        return description
    else:
        return '[no name] %s ' % resource_dict['id']

def resource_link(resource_dict, package_id):
    text = resource_display_name(resource_dict)
    url = url_for(controller='package',
        action='resource_read',
        id=package_id,
        resource_id=resource_dict['id'])
    return link_to(text, url)

def tag_link(tag):
    url = url_for(controller='tag', action='read', id=tag['name'])
    return link_to(tag['name'], url)

def group_link(group):
    url = url_for(controller='group', action='read', id=group['name'])
    return link_to(group['name'], url)
