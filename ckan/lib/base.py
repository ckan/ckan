# encoding: utf-8

"""The base functionality for web-views.

Provides functions for rendering templates, aborting the request, etc.

"""
from __future__ import annotations

import logging
from typing import Any, NoReturn, Optional

from jinja2.exceptions import TemplateNotFound, TemplatesNotFound

from flask import (
    render_template as flask_render_template,
    abort as flask_abort
)

import ckan.lib.helpers as h
import ckan.plugins as p

from ckan.common import request, config, session, g

log = logging.getLogger(__name__)

APIKEY_HEADER_NAME_KEY = 'apikey_header_name'
APIKEY_HEADER_NAME_DEFAULT = 'X-CKAN-API-Key'


def abort(status_code: int,
          detail: str = '',
          headers: Optional[dict[str, Any]] = None,
          comment: Optional[str] = None) -> NoReturn:
    '''Abort the current request immediately by returning an HTTP exception.

    This is a wrapper for :py:func:`flask.abort` that adds
    some CKAN custom behavior, including allowing
    :py:class:`~ckan.plugins.interfaces.IAuthenticator` plugins to alter the
    abort response, and showing flash messages in the web interface.

    '''
    if status_code == 403:
        # Allow IAuthenticator plugins to alter the abort
        for item in p.PluginImplementations(p.IAuthenticator):
            result = item.abort(status_code, detail, headers, comment)
            (status_code, detail, headers, comment) = result

    if detail and status_code != 503:
        h.flash_error(detail)

    flask_abort(status_code, detail)


def render_snippet(*template_names: str, **kw: Any) -> str:
    ''' Helper function for rendering snippets. Rendered html has
    comment tags added to show the template used. NOTE: unlike other
    render functions this takes a list of keywords instead of a dict for
    the extra template variables.

    :param template_names: the template to render, optionally with fallback
        values, for when the template can't be found. For each, specify the
        relative path to the template inside the registered tpl_dir.
    :type template_names: str
    :param kw: extra template variables to supply to the template
    :type kw: named arguments of any type that are supported by the template
    '''

    last_exc = None
    for template_name in template_names:
        try:
            output = render(template_name, extra_vars=kw)
            if config.get('debug'):
                output = (
                    '\n<!-- Snippet %s start -->\n%s\n<!-- Snippet %s end -->'
                    '\n' % (template_name, output, template_name))
            return h.literal(output)
        except TemplateNotFound as exc:
            if exc.name == template_name:
                # the specified template doesn't exist - try the next
                # fallback, but store the exception in case it was
                # last one
                last_exc = exc
                continue
            # a nested template doesn't exist - don't fallback
            raise exc
    else:
        raise last_exc or TemplatesNotFound(template_names)


def render(template_name: str,
           extra_vars: Optional[dict[str, Any]] = None) -> str:
    '''Render a template and return the output.

    This is CKAN's main template rendering function.

    :params template_name: relative path to template inside registered tpl_dir
    :type template_name: str
    :params extra_vars: additional variables available in template
    :type extra_vars: dict

    '''
    if extra_vars is None:
        extra_vars = {}

    _allow_caching()
    return flask_render_template(template_name, **extra_vars)


def _allow_caching(cache_force: Optional[bool] = None):
    # Caching Logic

    allow_cache = True
    # Force cache or not if explicit.
    if cache_force is not None:
        allow_cache = cache_force
    # Do not allow caching of pages for logged in users/flash messages etc.
    elif ('user' in g and g.user) or _is_valid_session_cookie_data():
        allow_cache = False
    # Tests etc.
    elif session.get("_user_id"):
        allow_cache = False
    # Don't cache if based on a non-cachable template used in this.
    elif request.environ.get('__no_cache__'):
        allow_cache = False
    # Don't cache if we have set the __no_cache__ param in the query string.
    elif request.args.get('__no_cache__'):
        allow_cache = False
    # Don't cache if caching is not enabled in config
    elif not config.get('ckan.cache_enabled'):
        allow_cache = False

    if not allow_cache:
        # Prevent any further rendering from being cached.
        request.environ['__no_cache__'] = True


def _is_valid_session_cookie_data() -> bool:
    is_valid_cookie_data = False
    for key, value in session.items():
        if key == config.get("WTF_CSRF_FIELD_NAME"):
            continue
        if not key.startswith(u'_') and value:
            is_valid_cookie_data = True
            break

    return is_valid_cookie_data
