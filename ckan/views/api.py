import cgi
import logging

from flask import request, make_response, g, redirect, url_for
from werkzeug.exceptions import BadRequest
from flask.ext.classy import FlaskView, route


import ckan.model as model
from ckan.common import json, _

from ckan.lib.navl.dictization_functions import DataError
from ckan.logic import get_action, ValidationError, NotFound, NotAuthorized
from ckan.lib.search import SearchError, SearchIndexError, SearchQueryError
import ckan.plugins as p


log = logging.getLogger(__name__)

CONTENT_TYPES = {
    'text': 'text/plain;charset=utf-8',
    'html': 'text/html;charset=utf-8',
    'json': 'application/json;charset=utf-8',
}


APIKEY_HEADER_NAME_KEY = 'apikey_header_name'
APIKEY_HEADER_NAME_DEFAULT = 'X-CKAN-API-Key'


# TODO:
def _(string):
    return string


def _identify_user():
    '''Try to identify the user
    If the user is identified then:
      g.user = user name (unicode)
      g.userobj = user object
      g.author = user name
    otherwise:
      g.user = None
      g.userobj = None
      g.author = user's IP address (unicode)'''
    # see if it was proxied first
    g.remote_addr = request.environ.get('HTTP_X_FORWARDED_FOR', '')
    if not g.remote_addr:
        g.remote_addr = request.environ.get('REMOTE_ADDR',
                                            'Unknown IP Address')

    # TODO:
    # Authentication plugins get a chance to run here break as soon as a
    # user is identified.
    # authenticators = p.PluginImplementations(p.IAuthenticator)
    # if authenticators:
    #    for item in authenticators:
    #        item.identify()
    #        if c.user:
    #            break

    # We haven't identified the user so try the default methods
    if not getattr(g, 'user', None):
        _identify_user_default()

    # If we have a user but not the userobj let's get the userobj.  This
    # means that IAuthenticator extensions do not need to access the user
    # model directly.
    if g.user and not getattr(g, 'userobj', None):
        g.userobj = model.User.by_name(g.user)

    # general settings
    if g.user:
        g.author = g.user
    else:
        g.author = g.remote_addr
    g.author = unicode(g.author)


def _identify_user_default():
    '''
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
    g.user = request.environ.get('REMOTE_USER', '')
    if g.user:
        g.user = g.user.decode('utf8')
        g.userobj = model.User.by_name(g.user)
        if g.userobj is None or not g.userobj.is_active():
            # This occurs when a user that was still logged in is deleted,
            # or when you are logged in, clean db
            # and then restart (or when you change your username)
            # There is no user object, so even though repoze thinks you
            # are logged in and your cookie has ckan_display_name, we
            # need to force user to logout and login again to get the
            # User object.

            # TODO: this should not be done here
            # session['lang'] = request.environ.get('CKAN_LANG')
            # session.save()
            ev = request.environ
            if 'repoze.who.plugins' in ev:
                pth = getattr(ev['repoze.who.plugins']['friendlyform'],
                              'logout_handler_path')
                redirect(pth)
    else:
        g.userobj = _get_user_for_apikey()
        if g.userobj is not None:
            g.user = g.userobj.name


def _get_user_for_apikey():
    # TODO: use config
    # apikey_header_name = config.get(APIKEY_HEADER_NAME_KEY,
    #                                APIKEY_HEADER_NAME_DEFAULT)
    apikey_header_name = APIKEY_HEADER_NAME_DEFAULT
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
    log.debug("Received API Key: %s" % apikey)
    apikey = unicode(apikey)
    query = model.Session.query(model.User)
    user = query.filter_by(apikey=apikey).first()
    return user


class ApiView(FlaskView):

    def _finish(self, status_int, response_data=None,
                content_type='text', headers=None):
        '''When a controller method has completed, call this method
        to prepare the response.
        @return response message - return this value from the controller
                                   method
                 e.g. return self._finish(404, 'Package not found')
        '''
        assert(isinstance(status_int, int))
        response_msg = ''
        if headers is None:
            headers = {}
        if response_data is not None:
            headers['Content-Type'] = CONTENT_TYPES[content_type]
            if content_type == 'json':
                response_msg = json.dumps(
                    response_data,
                    for_json=True)  # handle objects with for_json methods
            else:
                response_msg = response_data
            # Support "JSONP" callback.
            if (status_int == 200 and 'callback' in request.args and
                    request.method == 'GET'):
                # escape callback to remove '<', '&', '>' chars
                callback = cgi.escape(request.args['callback'])
                response_msg = self._wrap_jsonp(callback, response_msg)
        return make_response((response_msg, status_int, headers))

    def _finish_ok(self, response_data=None,
                   content_type='json',
                   resource_location=None):
        '''If a controller method has completed successfully then
        calling this method will prepare the response.
        @param resource_location - specify this if a new
           resource has just been created.
        @return response message - return this value from the controller
                                   method
                                   e.g. return self._finish_ok(pkg_dict)
        '''
        status_int = 200
        headers = None
        if resource_location:
            status_int = 201
            try:
                resource_location = str(resource_location)
            except Exception, inst:
                msg = \
                    "Couldn't convert '%s' header value '%s' to string: %s" % \
                    ('Location', resource_location, inst)
                raise Exception(msg)
            headers = {'Location': resource_location}

        return self._finish(status_int, response_data, content_type, headers)

    def _finish_not_authz(self, extra_msg=None):
        response_data = _('Access denied')
        if extra_msg:
            response_data = '%s - %s' % (response_data, extra_msg)
        return self._finish(403, response_data, 'json')

    def _finish_not_found(self, extra_msg=None):
        response_data = _('Not found')
        if extra_msg:
            response_data = '%s - %s' % (response_data, extra_msg)
        return self._finish(404, response_data, 'json')

    def _finish_bad_request(self, extra_msg=None):
        response_data = _('Bad request')
        if extra_msg:
            response_data = '%s - %s' % (response_data, extra_msg)
        return self._finish(400, response_data, 'json')

    def _wrap_jsonp(self, callback, response_msg):
        return '%s(%s);' % (callback, response_msg)

    # TODO: Check multiple endpoints http://stackoverflow.com/a/7876088/105987
    @route('/3/action/<logic_function>', endpoint='action',
           methods=['GET', 'POST'])
    @route('/action/<logic_function>', methods=['GET', 'POST'])
    def action(self, logic_function, ver=None):
        try:
            function = get_action(logic_function)
        except KeyError:
            msg = 'Action name not known: {0}'.format(logic_function)
            log.info(msg)
            return self._finish_bad_request(msg)

        # TODO: Abstract to base class
        _identify_user()

        context = {'model': model, 'session': model.Session, 'user': g.user,
                   'api_version': ver, 'return_type': 'LazyJSONObject',
                   'auth_user_obj': g.userobj}
        model.Session()._context = context

#        if g.user:
#            out = 'Action {0} found, user logged in: {1}' \
#                .format(logic_function, g.userobj.name)
#        else:
#            out = 'Action {0} found, user not logged in or not found' \
#                .format(logic_function)

#        return self._finish_ok(out)

        # TODO: use Flask's?
        return_dict = {'help': url_for('action',
                                       logic_function='help_show',
                                       ver=ver,
                                       name=logic_function,
                                       _external=True,
                                       )
                       }
        try:
            side_effect_free = getattr(function, 'side_effect_free', False)

            request_data = self._get_request_data(
                try_url_params=side_effect_free)
        except ValueError, inst:
            log.info('Bad Action API request data: %s', inst)
            return self._finish_bad_request(
                _('JSON Error: %s') % inst)
        if not isinstance(request_data, dict):
            # this occurs if request_data is blank
            log.info('Bad Action API request data - not dict: %r',
                     request_data)
            return self._finish_bad_request(
                _('Bad request data: %s') %
                'Request data JSON decoded to %r but '
                'it needs to be a dictionary.' % request_data)

        # if callback is specified we do not want to send that to the search
        if 'callback' in request_data:
            del request_data['callback']
            g.user = None
            g.userobj = None
            context['user'] = None
            context['auth_user_obj'] = None
        try:
            result = function(context, request_data)
            return_dict['success'] = True
            return_dict['result'] = result
        except DataError, e:
            log.info('Format incorrect (Action API): %s - %s',
                     e.error, request_data)
            return_dict['error'] = {'__type': 'Integrity Error',
                                    'message': e.error,
                                    'data': request_data}
            return_dict['success'] = False
            return self._finish(400, return_dict, content_type='json')
        except NotAuthorized, e:
            return_dict['error'] = {'__type': 'Authorization Error',
                                    'message': _('Access denied')}
            return_dict['success'] = False

            if unicode(e):
                return_dict['error']['message'] += u': %s' % e

            return self._finish(403, return_dict, content_type='json')
        except NotFound, e:
            return_dict['error'] = {'__type': 'Not Found Error',
                                    'message': _('Not found')}
            if unicode(e):
                return_dict['error']['message'] += u': %s' % e
            return_dict['success'] = False
            return self._finish(404, return_dict, content_type='json')
        except ValidationError, e:
            error_dict = e.error_dict
            error_dict['__type'] = 'Validation Error'
            return_dict['error'] = error_dict
            return_dict['success'] = False
            # CS nasty_string ignore
            log.info('Validation error (Action API): %r', str(e.error_dict))
            return self._finish(409, return_dict, content_type='json')
        except SearchQueryError, e:
            return_dict['error'] = {'__type': 'Search Query Error',
                                    'message': 'Search Query is invalid: %r' %
                                    e.args}
            return_dict['success'] = False
            return self._finish(400, return_dict, content_type='json')
        except SearchError, e:
            return_dict['error'] = {'__type': 'Search Error',
                                    'message': 'Search error: %r' % e.args}
            return_dict['success'] = False
            return self._finish(409, return_dict, content_type='json')
        except SearchIndexError, e:
            return_dict['error'] = {
                '__type': 'Search Index Error',
                'message': 'Unable to add package to search index: %s' %
                           str(e)}
            return_dict['success'] = False
            return self._finish(500, return_dict, content_type='json')
        return self._finish_ok(return_dict)

    @classmethod
    def _get_request_data(cls, try_url_params=False):
        '''Returns a dictionary, extracted from a request.

        If there is no data, None or "" is returned.
        ValueError will be raised if the data is not a JSON-formatted dict.

        The data is retrieved as a JSON-encoded dictionary from the request
        body.  Or, if the `try_url_params` argument is True and the request is
        a GET request, then an attempt is made to read the data from the url
        parameters of the request.

        try_url_params
            If try_url_params is False, then the data_dict is read from the
            request body.

            If try_url_params is True and the request is a GET request then the
            data is read from the url parameters.  The resulting dict will only
            be 1 level deep, with the url-param fields being the keys.  If a
            single key has more than one value specified, then the value will
            be a list of strings, otherwise just a string.

        '''
        def make_unicode(entity):
            '''Cast bare strings and strings in lists or dicts to Unicode. '''
            if isinstance(entity, str):
                return unicode(entity)
            elif isinstance(entity, list):
                new_items = []
                for item in entity:
                    new_items.append(make_unicode(item))
                return new_items
            elif isinstance(entity, dict):
                new_dict = {}
                for key, val in entity.items():
                    new_dict[key] = make_unicode(val)
                return new_dict
            else:
                return entity

        def mixed(multi_dict):
            '''Return a dict with values being lists if they have more than one
               item or a string otherwise
            '''
            out = {}
            for key, value in multi_dict.to_dict(flat=False).iteritems():
                out[key] = value[0] if len(value) == 1 else value
            return out

        request_data = {}
        if request.method == 'POST' and request.form:
            if (len(request.form.values()) == 1 and
                    request.form.values()[0] in [u'1', u'']):
                try:
                    request_data = json.loads(request.form.keys()[0])
                except ValueError, e:
                    raise ValueError(
                        'Error decoding JSON data. '
                        'Error: %r '
                        'JSON data extracted from the request: %r' %
                        (e, request_data))
            else:
                request_data = mixed(request.form)
        elif request.args and try_url_params:
            request_data = mixed(request.args)
        elif (request.data and request.data != '' and
              request.content_type != 'multipart/form-data'):
            try:
                request_data = request.get_json()
            except BadRequest, e:
                raise ValueError('Error decoding JSON data. '
                                 'Error: %r '
                                 'JSON data extracted from the request: %r' %
                                 (e, request_data))
            if not isinstance(request_data, dict):
                raise ValueError('Request data JSON decoded to %r but '
                                 'it needs to be a dictionary.' % request_data)
        if request_data:
            # ensure unicode values
            for key, val in request_data.items():
                # if val is str then assume it is ascii, since json converts
                # utf8 encoded JSON to unicode
                request_data[key] = make_unicode(val)
        log.debug('Request data extracted: %r', request_data)
        return request_data
