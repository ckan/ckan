# encoding: utf-8

"""The base Controller API

Provides the BaseController class for subclassing.
"""
import logging
import time
import inspect
import sys

from jinja2.exceptions import TemplateNotFound

import six
from flask import (
    render_template as flask_render_template,
    abort as flask_abort
)

import ckan.lib.i18n as i18n
import ckan.lib.render as render_
import ckan.lib.helpers as h
import ckan.lib.app_globals as app_globals
import ckan.plugins as p
import ckan.model as model
from ckan.views import (identify_user,
                        set_cors_headers_for_response,
                        check_session_cookie,
                        )
from ckan.common import (c, request, config,
                         session, asbool)


log = logging.getLogger(__name__)

APIKEY_HEADER_NAME_KEY = 'apikey_header_name'
APIKEY_HEADER_NAME_DEFAULT = 'X-CKAN-API-Key'


def abort(status_code=None, detail='', headers=None, comment=None):
    '''Abort the current request immediately by returning an HTTP exception.

    This is a wrapper for :py:func:`pylons.controllers.util.abort` that adds
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


def render_snippet(*template_names, **kw):
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
        raise last_exc or TemplateNotFound


def render_jinja2(template_name, extra_vars):
    env = config['pylons.app_globals'].jinja_env
    template = env.get_template(template_name)
    return template.render(**extra_vars)


def render(template_name, extra_vars=None, *pargs, **kwargs):
    '''Render a template and return the output.

    This is CKAN's main template rendering function.

    :params template_name: relative path to template inside registered tpl_dir
    :type template_name: str
    :params extra_vars: additional variables available in template
    :type extra_vars: dict
    :params pargs: DEPRECATED
    :type pargs: tuple
    :params kwargs: DEPRECATED
    :type kwargs: dict

    '''
    if pargs or kwargs:
        tb = inspect.getframeinfo(sys._getframe(1))
        log.warning(
            'Extra arguments to `base.render` are deprecated: ' +
            '<{0.filename}:{0.lineno}>'.format(tb)
        )

    if extra_vars is None:
        extra_vars = {}

    _allow_caching()
    return flask_render_template(template_name, **extra_vars)


def _allow_caching(cache_force=None):
    # Caching Logic

    allow_cache = True
    # Force cache or not if explicit.
    if cache_force is not None:
        allow_cache = cache_force
    # Do not allow caching of pages for logged in users/flash messages etc.
    elif _is_valid_session_cookie_data():
        allow_cache = False
    # Tests etc.
    elif 'REMOTE_USER' in request.environ:
        allow_cache = False
    # Don't cache if based on a non-cachable template used in this.
    elif request.environ.get('__no_cache__'):
        allow_cache = False
    # Don't cache if we have set the __no_cache__ param in the query string.
    elif request.params.get('__no_cache__'):
        allow_cache = False
    # Don't cache if caching is not enabled in config
    elif not asbool(config.get('ckan.cache_enabled', False)):
        allow_cache = False

    if not allow_cache:
        # Prevent any further rendering from being cached.
        request.environ['__no_cache__'] = True


def _is_valid_session_cookie_data():
    is_valid_cookie_data = False
    for key, value in session.items():
        if not key.startswith(u'_') and value:
            is_valid_cookie_data = True
            break

    return is_valid_cookie_data


class ValidationException(Exception):
    pass
