"""The base Controller API

Provides the BaseController class for subclassing.
"""
import logging
import time

from paste.deploy.converters import asbool
from pylons import cache, config, session
from pylons.controllers import WSGIController
from pylons.controllers.util import abort as _abort
from pylons.controllers.util import redirect_to, redirect
from pylons.decorators import jsonify, validate
from pylons.i18n import N_, gettext, ngettext
from pylons.templating import cached_template, pylons_globals
from genshi.template import MarkupTemplate
from genshi.template.text import NewTextTemplate
from webhelpers.html import literal

import ckan.exceptions
import ckan
import ckan.lib.i18n as i18n
import ckan.lib.render as render_
import ckan.lib.helpers as h
import ckan.lib.app_globals as app_globals
import ckan.plugins as p
import ckan.model as model
import ckan.lib.maintain as maintain

# These imports are for legacy usages and will be removed soon these should
# be imported directly from ckan.common for internal ckan code and via the
# plugins.toolkit for extensions.
from ckan.common import json, _, ungettext, c, g, request, response

log = logging.getLogger(__name__)

PAGINATE_ITEMS_PER_PAGE = 50

APIKEY_HEADER_NAME_KEY = 'apikey_header_name'
APIKEY_HEADER_NAME_DEFAULT = 'X-CKAN-API-Key'

ALLOWED_FIELDSET_PARAMS = ['package_form', 'restrict']


def abort(status_code=None, detail='', headers=None, comment=None):
    '''Abort the current request immediately by returning an HTTP exception.

    This is a wrapper for :py:func:`pylons.controllers.util.abort` that adds
    some CKAN custom behavior, including allowing
    :py:class:`~ckan.plugins.interfaces.IAuthenticator` plugins to alter the
    abort response, and showing flash messages in the web interface.

    '''
    if status_code == 401:
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
    output = '\n<!-- Snippet %s start -->\n%s\n<!-- Snippet %s end -->\n' % (
        template_name, output, template_name)
    return literal(output)


def render_text(template_name, extra_vars=None, cache_force=None):
    '''Render a Genshi :py:class:`NewTextTemplate`.

    This is just a wrapper function that lets you render a Genshi
    :py:class:`NewTextTemplate` without having to pass ``method='text'`` or
    ``loader_class=NewTextTemplate`` (it passes them to
    :py:func:`~ckan.plugins.toolkit.render` for you).

    '''
    return render(template_name,
                  extra_vars=extra_vars,
                  cache_force=cache_force,
                  method='text',
                  loader_class=NewTextTemplate)


def render_jinja2(template_name, extra_vars):
    env = config['pylons.app_globals'].jinja_env
    template = env.get_template(template_name)
    return template.render(**extra_vars)


def render(template_name, extra_vars=None, cache_key=None, cache_type=None,
           cache_expire=None, method='xhtml', loader_class=MarkupTemplate,
           cache_force=None, renderer=None):
    '''Render a template and return the output.

    This is CKAN's main template rendering function.

    .. todo::

       Document the parameters of :py:func:`ckan.plugins.toolkit.render`.

    '''
    def render_template():
        globs = extra_vars or {}
        globs.update(pylons_globals())
        globs['actions'] = model.Action

        # Using pylons.url() directly destroys the localisation stuff so
        # we remove it so any bad templates crash and burn
        del globs['url']

        try:
            template_path, template_type = render_.template_info(template_name)
        except render_.TemplateNotFound:
            raise

        # snippets should not pass the context
        # but allow for legacy genshi templates
        if renderer == 'snippet' and template_type != 'genshi':
            del globs['c']
            del globs['tmpl_context']

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

        # Jinja2 templates
        if template_type == 'jinja2':
            # We don't want to have the config in templates it should be
            # accessed via g (app_globals) as this gives us flexability such
            # as changing via database settings.
            del globs['config']
            # TODO should we raise error if genshi filters??
            return render_jinja2(template_name, globs)

        # Genshi templates
        template = globs['app_globals'].genshi_loader.load(
            template_name.encode('utf-8'), cls=loader_class
        )
        stream = template.generate(**globs)

        for item in p.PluginImplementations(p.IGenshiStreamFilter):
            stream = item.filter(stream)

        if loader_class == NewTextTemplate:
            return literal(stream.render(method="text", encoding=None))

        return literal(stream.render(method=method, encoding=None,
                                     strip_whitespace=True))

    if 'Pragma' in response.headers:
        del response.headers["Pragma"]

    ## Caching Logic
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
    log.debug('Template cache-control: %s' % response.headers["Cache-Control"])

    # Render Time :)
    try:
        return cached_template(template_name, render_template,
                               loader_class=loader_class)
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
        c.__version__ = ckan.__version__
        app_globals.app_globals._check_uptodate()

        self._identify_user()

        i18n.handle_request(request, c)

        maintain.deprecate_context_item(
            'new_activities',
            'Use `h.new_activities` instead.')

    def _identify_user(self):
        '''Try to identify the user
        If the user is identified then:
          c.user = user name (unicode)
          c.userobj = user object
          c.author = user name
        otherwise:
          c.user = None
          c.userobj = None
          c.author = user's IP address (unicode)'''
        # see if it was proxied first
        c.remote_addr = request.environ.get('HTTP_X_FORWARDED_FOR', '')
        if not c.remote_addr:
            c.remote_addr = request.environ.get('REMOTE_ADDR',
                                                'Unknown IP Address')

        # Authentication plugins get a chance to run here break as soon as a
        # user is identified.
        authenticators = p.PluginImplementations(p.IAuthenticator)
        if authenticators:
            for item in authenticators:
                item.identify()
                if c.user:
                    break

        # We haven't identified the user so try the default methods
        if not c.user:
            self._identify_user_default()

        # If we have a user but not the userobj let's get the userobj.  This
        # means that IAuthenticator extensions do not need to access the user
        # model directly.
        if c.user and not c.userobj:
            c.userobj = model.User.by_name(c.user)

        # general settings
        if c.user:
            c.author = c.user
        else:
            c.author = c.remote_addr
        c.author = unicode(c.author)

    def _identify_user_default(self):
        '''
        Identifies the user using two methods:
        a) If they logged into the web interface then repoze.who will
           set REMOTE_USER.
        b) For API calls they may set a header with an API key.
        '''

        # environ['REMOTE_USER'] is set by repoze.who if it authenticates
        # a user's cookie or OpenID. But repoze.who doesn't check the user
        # (still) exists in our database - we need to do that here. (Another
        # way would be with an userid_checker, but that would mean another db
        # access.
        # See: http://docs.repoze.org/who/1.0/narr.html#module-repoze.who\
        # .plugins.sql )
        c.user = request.environ.get('REMOTE_USER', '')
        if c.user:
            c.user = c.user.decode('utf8')
            c.userobj = model.User.by_name(c.user)
            if c.userobj is None or not c.userobj.is_active():
                # This occurs when a user that was still logged in is deleted,
                # or when you are logged in, clean db
                # and then restart (or when you change your username)
                # There is no user object, so even though repoze thinks you
                # are logged in and your cookie has ckan_display_name, we
                # need to force user to logout and login again to get the
                # User object.
                session['lang'] = request.environ.get('CKAN_LANG')
                session.save()

                ev = request.environ
                if 'repoze.who.plugins' in ev:
                    pth = getattr(ev['repoze.who.plugins']['friendlyform'],
                                  'logout_handler_path')
                    h.redirect_to(pth)
        else:
            c.userobj = self._get_user_for_apikey()
            if c.userobj is not None:
                c.user = c.userobj.name

    def __call__(self, environ, start_response):
        """Invoke the Controller"""
        # WSGIController.__call__ dispatches to the Controller method
        # the request is routed to. This routing information is
        # available in environ['pylons.routes_dict']

        try:
            res = WSGIController.__call__(self, environ, start_response)
        finally:
            model.Session.remove()

        # Clean out any old cookies as they may contain api keys etc
        # This also improves the cachability of our pages as cookies
        # prevent proxy servers from caching content unless they have
        # been configured to ignore them.
        for cookie in request.cookies:
            if cookie.startswith('ckan') and cookie not in ['ckan']:
                response.delete_cookie(cookie)
            # Remove the ckan session cookie if not used e.g. logged out
            elif cookie == 'ckan' and not c.user:
                # Check session for valid data (including flash messages)
                # (DGU also uses session for a shopping basket-type behaviour)
                is_valid_cookie_data = False
                for key, value in session.items():
                    if not key.startswith('_') and value:
                        is_valid_cookie_data = True
                        break
                if not is_valid_cookie_data:
                    if session.id:
                        if not session.get('lang'):
                            self.log.debug('No session data any more - '
                                           'deleting session')
                            self.log.debug('Session: %r', session.items())
                            session.delete()
                    else:
                        response.delete_cookie(cookie)
                        self.log.debug('No session data any more - '
                                       'deleting session cookie')
            # Remove auth_tkt repoze.who cookie if user not logged in.
            elif cookie == 'auth_tkt' and not session.id:
                response.delete_cookie(cookie)

        return res

    def __after__(self, action, **params):
        self._set_cors()
        r_time = time.time() - c.__timer
        url = request.environ['CKAN_CURRENT_URL'].split('?')[0]
        log.info(' %s render time %.3f seconds' % (url, r_time))

    def _set_cors(self):
        response.headers['Access-Control-Allow-Origin'] = "*"
        response.headers['Access-Control-Allow-Methods'] = \
            "POST, PUT, GET, DELETE, OPTIONS"
        response.headers['Access-Control-Allow-Headers'] = \
            "X-CKAN-API-KEY, Authorization, Content-Type"

    def _get_user_for_apikey(self):
        apikey_header_name = config.get(APIKEY_HEADER_NAME_KEY,
                                        APIKEY_HEADER_NAME_DEFAULT)
        apikey = request.headers.get(apikey_header_name, '')
        if not apikey:
            apikey = request.environ.get(apikey_header_name, '')
        if not apikey:
            # For misunderstanding old documentation (now fixed).
            apikey = request.environ.get('HTTP_AUTHORIZATION', '')
        if not apikey:
            apikey = request.environ.get('Authorization', '')
            # Forget HTTP Auth credentials (they have spaces).
            if ' ' in apikey:
                apikey = ''
        if not apikey:
            return None
        self.log.debug("Received API Key: %s" % apikey)
        apikey = unicode(apikey)
        query = model.Session.query(model.User)
        user = query.filter_by(apikey=apikey).first()
        return user


# Include the '_' function in the public names
__all__ = [__name for __name in locals().keys() if not __name.startswith('_')
           or __name == '_']
