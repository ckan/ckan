# encoding: utf-8

"""The base Controller API

Provides the BaseController class for subclassing.
"""
import logging
import time

from pylons import cache
from pylons.controllers import WSGIController
from pylons.controllers.util import abort as _abort
from pylons.decorators import jsonify
from pylons.i18n import N_, gettext, ngettext
from pylons.templating import cached_template, pylons_globals
from webhelpers.html import literal

import ckan.exceptions
import ckan
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

# These imports are for legacy usages and will be removed soon these should
# be imported directly from ckan.common for internal ckan code and via the
# plugins.toolkit for extensions.
from ckan.common import (json, _, ungettext, c, request, response, config,
                         session)

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
    # #1267 Convert detail to plain text, since WebOb 0.9.7.1 (which comes
    # with Lucid) causes an exception when unicode is received.
    detail = detail.encode('utf8')
    return _abort(status_code=status_code,
                  detail=detail,
                  headers=headers,
                  comment=comment)


def render_snippet(template_name, **kw):
    ''' Helper function for rendering snippets. Rendered html has
    comment tags added to show the template used. NOTE: unlike other
    render functions this takes a list of keywords instead of a dict for
    the extra template variables. '''
    # allow cache_force to be set in render function
    cache_force = kw.pop('cache_force', None)
    output = render(template_name, extra_vars=kw, cache_force=cache_force,
                    renderer='snippet')
    if config.get('debug'):
        output = ('\n<!-- Snippet %s start -->\n%s\n<!-- Snippet %s end -->\n'
                  % (template_name, output, template_name))
    return literal(output)


def render_jinja2(template_name, extra_vars):
    env = config['pylons.app_globals'].jinja_env
    template = env.get_template(template_name)
    return template.render(**extra_vars)


def render(template_name, extra_vars=None, cache_key=None, cache_type=None,
           cache_expire=None, cache_force=None, renderer=None):
    '''Render a template and return the output.

    This is CKAN's main template rendering function.

    .. todo::

       Document the parameters of :py:func:`ckan.plugins.toolkit.render`.

    '''
    def render_template():
        globs = extra_vars or {}
        globs.update(pylons_globals())

        # Using pylons.url() directly destroys the localisation stuff so
        # we remove it so any bad templates crash and burn
        del globs['url']

        try:
            template_path, template_type = render_.template_info(template_name)
        except render_.TemplateNotFound:
            raise

        log.debug('rendering %s [%s]' % (template_path, template_type))
        if config.get('debug'):
            context_vars = globs.get('c')
            if context_vars:
                context_vars = dir(context_vars)
            debug_info = {'template_name': template_name,
                          'template_path': template_path,
                          'template_type': template_type,
                          'vars': globs,
                          'c_vars': context_vars,
                          'renderer': renderer}
            if 'CKAN_DEBUG_INFO' not in request.environ:
                request.environ['CKAN_DEBUG_INFO'] = []
            request.environ['CKAN_DEBUG_INFO'].append(debug_info)

        del globs['config']
        return render_jinja2(template_name, globs)

    if 'Pragma' in response.headers:
        del response.headers["Pragma"]

    # Caching Logic
    allow_cache = True
    # Force cache or not if explicit.
    if cache_force is not None:
        allow_cache = cache_force
    # Do not allow caching of pages for logged in users/flash messages etc.
    elif session.last_accessed:
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
    # Don't cache if we have extra vars containing data.
    elif extra_vars:
        for k, v in extra_vars.iteritems():
            allow_cache = False
            break
    # Record cachability for the page cache if enabled
    request.environ['CKAN_PAGE_CACHABLE'] = allow_cache

    if allow_cache:
        response.headers["Cache-Control"] = "public"
        try:
            cache_expire = int(config.get('ckan.cache_expires', 0))
            response.headers["Cache-Control"] += \
                ", max-age=%s, must-revalidate" % cache_expire
        except ValueError:
            pass
    else:
        # We do not want caching.
        response.headers["Cache-Control"] = "private"
        # Prevent any further rendering from being cached.
        request.environ['__no_cache__'] = True

    # Render Time :)
    try:
        return cached_template(template_name, render_template)
    except ckan.exceptions.CkanUrlException, e:
        raise ckan.exceptions.CkanUrlException(
            '\nAn Exception has been raised for template %s\n%s' %
            (template_name, e.message))
    except render_.TemplateNotFound:
        raise


class ValidationException(Exception):
    pass


class BaseController(WSGIController):
    '''Base class for CKAN controller classes to inherit from.

    '''
    repo = model.repo
    log = logging.getLogger(__name__)

    def __before__(self, action, **params):
        c.__timer = time.time()
        app_globals.app_globals._check_uptodate()

        identify_user()

        i18n.handle_request(request, c)

    def __call__(self, environ, start_response):
        """Invoke the Controller"""
        # WSGIController.__call__ dispatches to the Controller method
        # the request is routed to. This routing information is
        # available in environ['pylons.routes_dict']

        try:
            res = WSGIController.__call__(self, environ, start_response)
        finally:
            model.Session.remove()

        check_session_cookie(response)

        return res

    def __after__(self, action, **params):

        set_cors_headers_for_response(response)

        r_time = time.time() - c.__timer
        url = request.environ['CKAN_CURRENT_URL'].split('?')[0]
        log.info(' %s render time %.3f seconds' % (url, r_time))


# Include the '_' function in the public names
__all__ = [__name for __name in locals().keys() if not __name.startswith('_')
           or __name == '_']
