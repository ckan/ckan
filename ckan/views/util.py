# encoding: utf-8

from flask import Blueprint

import ckan.lib.base as base
from ckan.lib.helpers import helper_functions as h
from ckan.common import _, request
from ckan.types import Response

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

    return base.render('development/primer.html')


def custom_form_fields() -> str:
    return base.render(
        'snippets/custom_form_fields.html',
        {'extras': [{'key': 'key', 'value': 'value'}], 'errors': {}}
    )


util.add_url_rule(
    '/util/redirect', view_func=internal_redirect, methods=('GET', 'POST',))
util.add_url_rule('/testing/primer', view_func=primer)
util.add_url_rule('/testing/custom_form_fields', view_func=custom_form_fields)
