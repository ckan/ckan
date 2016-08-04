# encoding: utf-8

from flask import redirect
from pylons import config
from paste.deploy.converters import asbool

import ckan.model as model
from ckan.common import c, request, session
import ckan.plugins as p

import logging
log = logging.getLogger(__name__)

APIKEY_HEADER_NAME_KEY = u'apikey_header_name'
APIKEY_HEADER_NAME_DEFAULT = u'X-CKAN-API-Key'


def check_session_cookie(response):
    u'''
    The cookies for auth (auth_tkt) and session (ckan) are separate. This
    checks whether a user is logged in, and determines the validity of the
    session cookie, removing it if necessary.
    '''
    for cookie in request.cookies:
        # Remove the ckan session cookie if logged out.
        if cookie == u'ckan' and not c.user:
            # Check session for valid data (including flash messages)
            is_valid_cookie_data = False
            for key, value in session.items():
                if not key.startswith(u'_') and value:
                    is_valid_cookie_data = True
                    break
            if not is_valid_cookie_data:
                if session.id:
                    log.debug(u'No valid session data - deleting session')
                    log.debug(u'Session: %r', session.items())
                    session.delete()
                else:
                    log.debug(u'No session id - deleting session cookie')
                    response.delete_cookie(cookie)
        # Remove auth_tkt repoze.who cookie if user not logged in.
        elif cookie == u'auth_tkt' and not session.id:
            response.delete_cookie(cookie)

    return response


def set_cors_headers_for_response(response):
    u'''
    Set up Access Control Allow headers if either origin_allow_all is True, or
    the request Origin is in the origin_whitelist.
    '''
    if config.get(u'ckan.cors.origin_allow_all') \
       and request.headers.get(u'Origin'):

        cors_origin_allowed = None
        if asbool(config.get(u'ckan.cors.origin_allow_all')):
            cors_origin_allowed = u'*'
        elif config.get(u'ckan.cors.origin_whitelist') and \
                request.headers.get(u'Origin') \
                in config[u'ckan.cors.origin_whitelist'].split(u' '):
            # set var to the origin to allow it.
            cors_origin_allowed = request.headers.get(u'Origin')

        if cors_origin_allowed is not None:
            response.headers[u'Access-Control-Allow-Origin'] = \
                cors_origin_allowed
            response.headers[u'Access-Control-Allow-Methods'] = \
                u"POST, PUT, GET, DELETE, OPTIONS"
            response.headers[u'Access-Control-Allow-Headers'] = \
                u"X-CKAN-API-KEY, Authorization, Content-Type"

    return response


def identify_user():
    u'''Try to identify the user
    If the user is identified then:
      c.user = user name (unicode)
      c.userobj = user object
      c.author = user name
    otherwise:
      c.user = None
      c.userobj = None
      c.author = user's IP address (unicode)'''
    # see if it was proxied first
    c.remote_addr = request.environ.get(u'HTTP_X_FORWARDED_FOR', u'')
    if not c.remote_addr:
        c.remote_addr = request.environ.get(u'REMOTE_ADDR',
                                            u'Unknown IP Address')

    # Authentication plugins get a chance to run here break as soon as a user
    # is identified.
    authenticators = p.PluginImplementations(p.IAuthenticator)
    if authenticators:
        for item in authenticators:
            item.identify()
            if c.user:
                break

    # We haven't identified the user so try the default methods
    if not getattr(c, u'user', None):
        _identify_user_default()

    # If we have a user but not the userobj let's get the userobj. This means
    # that IAuthenticator extensions do not need to access the user model
    # directly.
    if c.user and not getattr(c, u'userobj', None):
        c.userobj = model.User.by_name(c.user)

    # general settings
    if c.user:
        c.author = c.user
    else:
        c.author = c.remote_addr
    c.author = unicode(c.author)


def _identify_user_default():
    u'''
    Identifies the user using two methods:
    a) If they logged into the web interface then repoze.who will
       set REMOTE_USER.
    b) For API calls they may set a header with an API key.
    '''

    # environ['REMOTE_USER'] is set by repoze.who if it authenticates a
    # user's cookie. But repoze.who doesn't check the user (still) exists
    # in our database - we need to do that here. (Another way would be
    # with an userid_checker, but that would mean another db access.
    # See: http://docs.repoze.org/who/1.0/narr.html#module-repoze.who\
    # .plugins.sql )
    c.user = request.environ.get(u'REMOTE_USER', u'')
    if c.user:
        c.user = c.user.decode(u'utf8')
        c.userobj = model.User.by_name(c.user)

        if c.userobj is None or not c.userobj.is_active():

            # This occurs when a user that was still logged in is deleted, or
            # when you are logged in, clean db and then restart (or when you
            # change your username). There is no user object, so even though
            # repoze thinks you are logged in and your cookie has
            # ckan_display_name, we need to force user to logout and login
            # again to get the User object.

            ev = request.environ
            if u'repoze.who.plugins' in ev:
                pth = getattr(ev[u'repoze.who.plugins'][u'friendlyform'],
                              u'logout_handler_path')
                redirect(pth)
    else:
        c.userobj = _get_user_for_apikey()
        if c.userobj is not None:
            c.user = c.userobj.name


def _get_user_for_apikey():
    # TODO: use config
    # apikey_header_name = config.get(APIKEY_HEADER_NAME_KEY,
    #                                APIKEY_HEADER_NAME_DEFAULT)
    apikey_header_name = APIKEY_HEADER_NAME_DEFAULT
    apikey = request.headers.get(apikey_header_name, u'')
    if not apikey:
        apikey = request.environ.get(apikey_header_name, u'')
    if not apikey:
        # For misunderstanding old documentation (now fixed).
        apikey = request.environ.get(u'HTTP_AUTHORIZATION', u'')
    if not apikey:
        apikey = request.environ.get(u'Authorization', u'')
        # Forget HTTP Auth credentials (they have spaces).
        if u' ' in apikey:
            apikey = u''
    if not apikey:
        return None
    log.debug(u'Received API Key: %s' % apikey)
    apikey = unicode(apikey)
    query = model.Session.query(model.User)
    user = query.filter_by(apikey=apikey).first()
    return user
