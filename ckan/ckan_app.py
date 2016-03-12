from flask import Flask, request

import ckan.model as model
import ckan.plugins as p

from ckan.controllers.flapi import ApiView

app = None
registry = None
translator_obj = None

def fake_pylons():
    import pylons
    from pylons.util import ContextObj, PylonsContext
    from paste.registry import Registry
    from pylons import translator
    from ckan.lib.cli import MockTranslator

    global registry
    global translator_obj

    c = pylons.util.AttribSafeContextObj()

    registry=Registry()
    registry.prepare()

    translator_obj=MockTranslator()

    registry.register(translator, translator_obj)
    registry.register(pylons.c, c)


def unfake_pylons(response):
    import pylons
    pylons.tmpl_context._pop_object()
    return response


def identify_user():
    '''Try to identify the user
    If the user is identified then:
      c.user = user name (unicode)
      c.userobj = user object
      c.author = user name
    otherwise:
      c.user = None
      c.userobj = None
      c.author = user's IP address (unicode)'''
    from ckan.common import c

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
        c.user, c.userobj = identify_user_default()

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

def identify_user_default():
    '''
    Identifies the user using two methods:
    a) If they logged into the web interface then repoze.who will
       set REMOTE_USER.
    b) For API calls they may set a header with an API key.
    '''
    from ckan.common import c

    # environ['REMOTE_USER'] is set by repoze.who if it authenticates a
    # user's cookie. But repoze.who doesn't check the user (still) exists
    # in our database - we need to do that here. (Another way would be
    # with an userid_checker, but that would mean another db access.
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
        c.userobj = get_user_for_apikey()
        if c.userobj is not None:
            c.user = c.userobj.name

    return c.user, c.userobj

def get_user_for_apikey():
    from ckan.common import config
    APIKEY_HEADER_NAME_KEY = 'apikey_header_name'
    APIKEY_HEADER_NAME_DEFAULT = 'X-CKAN-API-Key'

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

def create_app():
    global app
    app = Flask("ckan")
    app.debug = True

    app.before_request_funcs = {
        None: [fake_pylons, identify_user]
    }
    app.after_request_funcs = {
        None: [unfake_pylons]
    }

    ##############################################################################
    # Set up routes
    ##############################################################################
    app.add_url_rule('/api/3/action/<func_name>', view_func=ApiView.as_view('api'))

    return app


