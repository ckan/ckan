# coding=UTF-8

"""Helper functions

Consists of functions to typically be used within templates, but also
available to Controllers. This module is available to templates as 'h'.
"""
from webhelpers.html import escape, HTML, literal, url_escape
from webhelpers.html.tools import mail_to
from webhelpers.html.tags import *
from webhelpers.markdown import markdown
from webhelpers import paginate
from webhelpers.text import truncate
from pylons.decorators.cache import beaker_cache
from routes import url_for, redirect_to
from alphabet_paginate import AlphaPage
from lxml.html import fromstring

try:
    from collections import OrderedDict # from python 2.7
except ImportError:
    from sqlalchemy.util import OrderedDict

try:
    import json
except ImportError:
    import simplejson as json

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
    from ckan.authz import Authorizer
    if domain_object is None:
        from ckan import model
        domain_object = model.System()
    return Authorizer.am_authorized(c, action, domain_object)

def linked_user(user):
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
        _icon = icon("user") + " "
        return _icon + link_to(user.display_name, 
                       url_for(controller='user', action='read', id=_name))

def group_name_to_title(name):
    from ckan import model
    group = model.Group.by_name(name)
    if group is not None:
        return group.title
    return name

def markdown_extract(text):
    if (text is None) or (text == ''):
        return ''
    html = fromstring(markdown(text))
    plain = html.xpath("string()")
    return unicode(truncate(plain, length=190, indicator='...', whole_word=True))

def icon_url(name):
    return '/images/icons/%s.png' % name

def icon(name, alt=None):
    return literal('<img src="%s" height="16px" width="16px" alt="%s" /> ' % (icon_url(name), alt))

class Page(paginate.Page):
    
    # Curry the pager method of the webhelpers.paginate.Page class, so we have
    # our custom layout set as default.
    def pager(self, *args, **kwargs):
        kwargs.update(
            format=u"<div class='pager'>$link_previous ~2~ $link_next</div>",
            symbol_previous=u'« Prev', symbol_next=u'Next »'
        )
        return super(Page, self).pager(*args, **kwargs)


def render_datetime(datetime_):
    '''Render a datetime object as a string in a reasonable way (Y-m-d H:m).
    '''
    if datetime_:
        return datetime_.strftime('%Y-%m-%d %H:%M')
    else:
        return ''

