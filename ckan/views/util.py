# encoding: utf-8

from flask import Blueprint, g

import ckan.lib.base as base
from ckan.lib.helpers import helper_functions as h
from ckan.common import _, request
from ckan.types import Response

from markupsafe import escape
from flask_wtf.csrf import generate_csrf

util = Blueprint(u'util', __name__)


def internal_redirect() -> Response:
    u''' Redirect to the url parameter.
    Only internal URLs are allowed'''

    url = request.form.get(u'url') or request.args.get(u'url')
    if not url:
        base.abort(400, _(u'Missing Value') + u': url')

    url = url.replace('\r', ' ').replace('\n', ' ').replace('\0', ' ')
    if h.url_is_local(url):
        return h.redirect_to(url)
    else:
        base.abort(403, _(u'Redirecting to external site is not allowed.'))


def primer() -> str:
    u''' Render all HTML components out onto a single page.
    This is useful for development/styling of CKAN. '''

    return base.render(u'development/primer.html')


def csrf_input() -> str:
    # rendering a snippet is overkill for one tag
    return (
        f'<input type="hidden" name="{escape(g.csrf_field_name)}"'
        f' value="{escape(generate_csrf())}"/>'
    )


util.add_url_rule(
    u'/util/redirect', view_func=internal_redirect, methods=(u'GET', u'POST',))
util.add_url_rule(u'/testing/primer', view_func=primer)
util.add_url_rule('/csrf-input', view_func=csrf_input)
