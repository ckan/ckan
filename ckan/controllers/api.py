# encoding: utf-8

import os.path
import logging
import cgi

from six import text_type
from six.moves.urllib.parse import unquote_plus

import ckan.model as model
import ckan.logic as logic
import ckan.lib.base as base
import ckan.lib.helpers as h
import ckan.lib.search as search
import ckan.lib.navl.dictization_functions
import ckan.lib.jsonp as jsonp
import ckan.lib.munge as munge

from ckan.views import identify_user

from ckan.common import _, c, request, response
from six.moves import map


log = logging.getLogger(__name__)

# shortcuts
get_action = logic.get_action
NotAuthorized = logic.NotAuthorized
NotFound = logic.NotFound
ValidationError = logic.ValidationError
DataError = ckan.lib.navl.dictization_functions.DataError

IGNORE_FIELDS = ['q']
CONTENT_TYPES = {
    'text': 'text/plain;charset=utf-8',
    'html': 'text/html;charset=utf-8',
    'json': 'application/json;charset=utf-8',
    'javascript': 'application/javascript;charset=utf-8',
}


class ApiController(base.BaseController):

    _actions = {}

    def __call__(self, environ, start_response):
        # we need to intercept and fix the api version
        # as it will have a "/" at the start
        routes_dict = environ['pylons.routes_dict']
        api_version = routes_dict.get('ver')
        if api_version:
            api_version = api_version[1:]
            routes_dict['ver'] = int(api_version)

        identify_user()
        try:
            context = {'model': model, 'user': c.user,
                       'auth_user_obj': c.userobj}
            logic.check_access('site_read', context)
        except NotAuthorized:
            response_msg = self._finish(403,
                                        _('Not authorized to see this page'))
            # Call start_response manually instead of the parent __call__
            # because we want to end the request instead of continuing.
            response_msg = response_msg.encode('utf8')
            body = '%i %s' % (response.status_int, response_msg)
            start_response(body, response.headers.items())
            return [response_msg]

        # avoid status_code_redirect intercepting error responses
        environ['pylons.status_code_redirect'] = True
        return base.BaseController.__call__(self, environ, start_response)

    def _finish(self, status_int, response_data=None,
                content_type='text'):
        '''When a controller method has completed, call this method
        to prepare the response.
        @return response message - return this value from the controller
                                   method
                 e.g. return self._finish(404, 'Package not found')
        '''
        assert(isinstance(status_int, int))
        response.status_int = status_int
        response_msg = ''
        if response_data is not None:
            response.headers['Content-Type'] = CONTENT_TYPES[content_type]
            if content_type == 'json':
                response_msg = h.json.dumps(
                    response_data,
                    for_json=True)  # handle objects with for_json methods
            else:
                response_msg = response_data
            # Support "JSONP" callback.
            if (status_int == 200 and
                    'callback' in request.params and
                    request.method == 'GET'):
                # escape callback to remove '<', '&', '>' chars
                callback = cgi.escape(request.params['callback'])
                response_msg = self._wrap_jsonp(callback, response_msg)
                response.headers['Content-Type'] = CONTENT_TYPES['javascript']
        return response_msg

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
        if resource_location:
            status_int = 201
            self._set_response_header('Location', resource_location)
        else:
            status_int = 200

        return self._finish(status_int, response_data, content_type)

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

    def _set_response_header(self, name, value):
        try:
            value = str(value)
        except Exception as inst:
            msg = "Couldn't convert '%s' header value '%s' to string: %s" % \
                (name, value, inst)
            raise Exception(msg)
        response.headers[name] = value

    def get_api(self, ver=None):
        response_data = {}
        response_data['version'] = ver
        return self._finish_ok(response_data)

    def action(self, logic_function, ver=None):
        try:
            function = get_action(logic_function)
        except KeyError:
            log.info('Can\'t find logic function: %s', logic_function)
            return self._finish_bad_request(
                _('Action name not known: %s') % logic_function)

        context = {'model': model, 'session': model.Session, 'user': c.user,
                   'api_version': ver, 'auth_user_obj': c.userobj}
        model.Session()._context = context

        return_dict = {'help': h.url_for(controller='api',
                                         action='action',
                                         logic_function='help_show',
                                         ver=ver,
                                         name=logic_function,
                                         qualified=True,
                                         )
                       }
        try:
            side_effect_free = getattr(function, 'side_effect_free', False)
            request_data = self._get_request_data(
                try_url_params=side_effect_free)
        except ValueError as inst:
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
            c.user = None
            c.userobj = None
            context['user'] = None
            context['auth_user_obj'] = None
        try:
            result = function(context, request_data)
            return_dict['success'] = True
            return_dict['result'] = result
        except DataError as e:
            log.info('Format incorrect (Action API): %s - %s',
                     e.error, request_data)
            return_dict['error'] = {'__type': 'Integrity Error',
                                    'message': e.error,
                                    'data': request_data}
            return_dict['success'] = False
            return self._finish(400, return_dict, content_type='json')
        except NotAuthorized as e:
            return_dict['error'] = {'__type': 'Authorization Error',
                                    'message': _('Access denied')}
            return_dict['success'] = False

            if text_type(e):
                return_dict['error']['message'] += u': %s' % e

            return self._finish(403, return_dict, content_type='json')
        except NotFound as e:
            return_dict['error'] = {'__type': 'Not Found Error',
                                    'message': _('Not found')}
            if text_type(e):
                return_dict['error']['message'] += u': %s' % e
            return_dict['success'] = False
            return self._finish(404, return_dict, content_type='json')
        except ValidationError as e:
            error_dict = e.error_dict
            error_dict['__type'] = 'Validation Error'
            return_dict['error'] = error_dict
            return_dict['success'] = False
            # CS nasty_string ignore
            log.info('Validation error (Action API): %r', str(e.error_dict))
            return self._finish(409, return_dict, content_type='json')
        except search.SearchQueryError as e:
            return_dict['error'] = {'__type': 'Search Query Error',
                                    'message': 'Search Query is invalid: %r' %
                                    e.args}
            return_dict['success'] = False
            return self._finish(400, return_dict, content_type='json')
        except search.SearchError as e:
            return_dict['error'] = {'__type': 'Search Error',
                                    'message': 'Search error: %r' % e.args}
            return_dict['success'] = False
            return self._finish(409, return_dict, content_type='json')
        except search.SearchIndexError as e:
            return_dict['error'] = {
                '__type': 'Search Index Error',
                'message': 'Unable to add package to search index: %s' %
                           str(e)}
            return_dict['success'] = False
            return self._finish(500, return_dict, content_type='json')
        return self._finish_ok(return_dict)

    @jsonp.jsonpify
    def user_autocomplete(self):
        q = request.params.get('q', '')
        limit = request.params.get('limit', 20)
        user_list = []
        if q:
            context = {'model': model, 'session': model.Session,
                       'user': c.user, 'auth_user_obj': c.userobj}

            data_dict = {'q': q, 'limit': limit}

            user_list = get_action('user_autocomplete')(context, data_dict)
        return user_list

    @jsonp.jsonpify
    def group_autocomplete(self):
        q = request.params.get('q', '')
        t = request.params.get('type', None)
        limit = request.params.get('limit', 20)
        try:
            limit = int(limit)
        except ValueError:
            limit = 20
        limit = min(50, limit)

        query = model.Group.search_by_name_or_title(q, t)

        def convert_to_dict(user):
            out = {}
            for k in ['id', 'name', 'title']:
                out[k] = getattr(user, k)
            return out

        query = query.limit(limit)
        out = [convert_to_dict(q) for q in query.all()]
        return out

    @jsonp.jsonpify
    def organization_autocomplete(self):
        q = request.params.get('q', '')
        limit = request.params.get('limit', 20)
        organization_list = []

        if q:
            context = {'user': c.user, 'model': model}
            data_dict = {'q': q, 'limit': limit}
            organization_list = \
                get_action('organization_autocomplete')(context, data_dict)
        return organization_list

    def munge_package_name(self):
        name = request.params.get('name')
        munged_name = munge.munge_name(name)
        return self._finish_ok(munged_name)

    def munge_title_to_package_name(self):
        name = request.params.get('title') or request.params.get('name')
        munged_name = munge.munge_title_to_name(name)
        return self._finish_ok(munged_name)

    def munge_tag(self):
        tag = request.params.get('tag') or request.params.get('name')
        munged_tag = munge.munge_tag(tag)
        return self._finish_ok(munged_tag)

    def i18n_js_translations(self, lang):
        ''' translation strings for front end '''
        ckan_path = os.path.join(os.path.dirname(__file__), '..')
        source = os.path.abspath(os.path.join(ckan_path, 'public',
                                 'base', 'i18n', '%s.js' % lang))
        response.headers['Content-Type'] = CONTENT_TYPES['json']
        if not os.path.exists(source):
            return '{}'
        f = open(source, 'r')
        return(f)

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
                return text_type(entity)
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

        cls.log.debug('Retrieving request params: %r', request.params)
        cls.log.debug('Retrieving request POST: %r', request.POST)
        cls.log.debug('Retrieving request GET: %r', request.GET)
        request_data = None
        if request.POST and request.content_type == 'multipart/form-data':
            request_data = dict(request.POST)
        elif request.POST:
            try:
                keys = request.POST.keys()
                # Parsing breaks if there is a = in the value, so for now
                # we will check if the data is actually all in a single key
                if keys and request.POST[keys[0]] in [u'1', u'']:
                    request_data = keys[0]
                else:
                    request_data = unquote_plus(request.body)
            except Exception as inst:
                msg = "Could not find the POST data: %r : %s" % \
                      (request.POST, inst)
                raise ValueError(msg)

        elif try_url_params and request.GET:
            return request.GET.mixed()

        else:
            try:
                if request.method in ['POST', 'PUT']:
                    request_data = request.body
                else:
                    request_data = None
            except Exception as inst:
                msg = "Could not extract request body data: %s" % \
                      (inst)
                raise ValueError(msg)
            cls.log.debug('Retrieved request body: %r', request.body)
            if not request_data:
                if not try_url_params:
                    msg = "Invalid request. Please use POST method" \
                        " for your request"
                    raise ValueError(msg)
                else:
                    request_data = {}
        if request_data and request.content_type != 'multipart/form-data':
            try:
                request_data = h.json.loads(request_data, encoding='utf8')
            except ValueError as e:
                raise ValueError('Error decoding JSON data. '
                                 'Error: %r '
                                 'JSON data extracted from the request: %r' %
                                 (e, request_data))
            if not isinstance(request_data, dict):
                raise ValueError('Request data JSON decoded to %r but '
                                 'it needs to be a dictionary.' % request_data)
            # ensure unicode values
            for key, val in request_data.items():
                # if val is str then assume it is ascii, since json converts
                # utf8 encoded JSON to unicode
                request_data[key] = make_unicode(val)
        cls.log.debug('Request data extracted: %r', request_data)
        return request_data
