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
from routes import url_for, redirect_to
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
