# encoding: utf-8

import re

from flask import Blueprint

import ckan.lib.base as base
import ckan.lib.helpers as h
from ckan.common import _, request


util = Blueprint(u'util', __name__)


def internal_redirect():
    u''' Redirect to the url parameter.
    Only internal URLs are allowed'''

    url = request.form.get(u'url') or request.args.get(u'url')

    if not url:
        base.abort(400, _(u'Missing Value') + u': url')

    url = url.replace(u'\r', u' ').replace(u'\n', u' ').replace(u'\0', u' ')
    if h.url_is_local(url):
        return h.redirect_to(url)
    else:
        base.abort(403, _(u'Redirecting to external site is not allowed.'))


def primer():
    u''' Render all HTML components out onto a single page.
    This is useful for development/styling of CKAN. '''

    return base.render(u'development/primer.html')


util.add_url_rule(
    u'/util/redirect', view_func=internal_redirect, methods=(u'GET', u'POST',))
util.add_url_rule(u'/testing/primer', view_func=primer)
