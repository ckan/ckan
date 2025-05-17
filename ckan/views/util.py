# encoding: utf-8

from flask import Blueprint, jsonify, make_response
from flask_wtf.csrf import generate_csrf

import ckan.lib.base as base
from ckan.lib.helpers import helper_functions as h
from ckan.common import _, request, g, config
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


def _abort(status_code: int, detail: str) -> Response:
    headers = {u'Content-Type': "application/json;charset=utf-8"}
    return make_response((detail, status_code, headers))


def csrf_input() -> Response:
    """ Generate a CSRF token and return it in a JSON response for XHR POST requests.
    Note: CORS protects this endpoint cross domain in XHR/Fetch context"""
    origin = request.headers.get("Origin")
    if origin is None or origin == '':
        return _abort(400, "Origin header is missing.")

    domain = config.get('ckan.site_url')
    if g.debug:
        # return domain we received on.
        if "localhost" in origin:
            domain = origin

    # Handle preflight OPTIONS request
    if request.method == "OPTIONS":
        response = Response()
        response.headers["Access-Control-Allow-Origin"] = domain
        response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        return response

    # Handle GET request protections
    if 'application/json' not in request.accept_mimetypes:
        # Disallowing simple content types to ensure browser CORS checking
        return _abort(400, "Only application/json content-type accept is allowed.")

    if origin != domain:
        return _abort(400, "Origin not allowed.")

    if g.csrf_enabled:
        csrf_token = generate_csrf()
    else:
        csrf_token = "disabled"

    return jsonify({
            "name": g.csrf_field_name,
            "header": g.csrf_header_name,
            "token": csrf_token
        })


util.add_url_rule(
    '/util/redirect', view_func=internal_redirect, methods=('GET', 'POST',))
util.add_url_rule('/testing/primer', view_func=primer)
util.add_url_rule('/testing/custom_form_fields', view_func=custom_form_fields)
util.add_url_rule('/csrf-input', view_func=csrf_input, methods=('GET', 'OPTIONS'))
