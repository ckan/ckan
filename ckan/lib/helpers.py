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
try:
    import json
except Exception:
    import simplejson as json

# FIXME: shouldn't have to pass the c object in to this.
def nav_link(c, text, controller, **kwargs):
    return link_to(
        text, 
        url_for(controller=controller, **kwargs),
        class_=('active' if c.controller == controller else '')
    )

# FIXME: shouldn't have to pass the c object in to this.
def subnav_link(c, text, action, **kwargs):
    return link_to(
        text, 
        url_for(action=action, **kwargs),
        class_=('active' if c.action == action else '')
    )

@beaker_cache(expire=600, cache_response=False)
def linked_user(username):
    from ckan import model
    user = model.User.by_name(unicode(username))
    if user:
        return link_to(username, url_for(controller='user', action='read', id=user.id))
    return username

def icon_url(name):
    return '/images/icons/%s.png' % name

def icon(name, alt=None):
    return literal('<img src="%s" height="16px" width="16px" alt="%s" />' % (icon_url(name), alt))

class Page(paginate.Page):
    
    # Curry the pager method of the webhelpers.paginate.Page class, so we have
    # our custom layout set as default.
    def pager(self, *args, **kwargs):
        kwargs.update(
            format="<div class='pager'>$link_previous ~2~ $link_next</div>",
            symbol_previous='« Prev', symbol_next='Next »'
        )
        return super(Page, self).pager(*args, **kwargs)


def render_datetime(datetime_):
    '''Render a datetime object as a string in a reasonable way (Y-m-d H:m).
    '''
    if datetime_:
        return datetime_.strftime('%Y-%m-%d %H:%m')
    else:
        return ''

