# encoding: utf-8

import os
import logging
import html
import io

from flask import Blueprint, make_response
import six
from six import text_type
from werkzeug.exceptions import BadRequest

import ckan.model as model
from ckan.common import json, _, g, request
from ckan.lib.helpers import url_for
from ckan.lib.base import render
from ckan.lib.i18n import get_locales_from_config

from ckan.lib.navl.dictization_functions import DataError
from ckan.logic import get_action, ValidationError, NotFound, NotAuthorized
from ckan.lib.search import SearchError, SearchIndexError, SearchQueryError


log = logging.getLogger(__name__)

CONTENT_TYPES = {
    u'text': u'text/plain;charset=utf-8',
    u'html': u'text/html;charset=utf-8',
    u'json': u'application/json;charset=utf-8',
    u'javascript': u'application/javascript;charset=utf-8',
}

API_REST_DEFAULT_VERSION = 1

API_DEFAULT_VERSION = 3
API_MAX_VERSION = 3


api = Blueprint(u'api', __name__, url_prefix=u'/api')


def _finish(status_int, response_data=None,
            content_type=u'text', headers=None):
    u'''When a controller method has completed, call this method
    to prepare the response.

    :param status_int: The HTTP status code to return
    :type status_int: int
    :param response_data: The body of the response
    :type response_data: object if content_type is `text` or `json`,
        a string otherwise
    :param content_type: One of `text`, `html` or `json`. Defaults to `text`
    :type content_type: string
    :param headers: Extra headers to serve with the response
    :type headers: dict

    :rtype: response object. Return this value from the view function
        e.g. return _finish(404, 'Dataset not found')
    '''
    assert(isinstance(status_int, int))
    response_msg = u''
    if headers is None:
        headers = {}
    if response_data is not None:
        headers[u'Content-Type'] = CONTENT_TYPES[content_type]
        if content_type == u'json':
            response_msg = json.dumps(
                response_data,
                for_json=True)  # handle objects with for_json methods
        else:
            response_msg = response_data
        # Support JSONP callback.
        if (status_int == 200 and u'callback' in request.args and
                request.method == u'GET'):
            # escape callback to remove '<', '&', '>' chars
            callback = html.escape(request.args[u'callback'])
            response_msg = _wrap_jsonp(callback, response_msg)
            headers[u'Content-Type'] = CONTENT_TYPES[u'javascript']
    return make_response((response_msg, status_int, headers))


def _finish_ok(response_data=None,
               content_type=u'json',
               resource_location=None):
    u'''If a controller method has completed successfully then
    calling this method will prepare the response.

    :param response_data: The body of the response
    :type response_data: object if content_type is `text` or `json`,
        a string otherwise
    :param content_type: One of `text`, `html` or `json`. Defaults to `json`
    :type content_type: string
    :param resource_location: Specify this if a new resource has just been
        created and you need to add a `Location` header
    :type headers: string

    :rtype: response object. Return this value from the view function
        e.g. return _finish_ok(pkg_dict)
    '''
    status_int = 200
    headers = None
    if resource_location:
        status_int = 201
        try:
            resource_location = str(resource_location)
        except Exception as inst:
            msg = \
                u"Couldn't convert '%s' header value '%s' to string: %s" % \
                (u'Location', resource_location, inst)
            raise Exception(msg)
        headers = {u'Location': resource_location}

    return _finish(status_int, response_data, content_type, headers)


def _finish_not_authz(extra_msg=None):
    response_data = _(u'Access denied')
    if extra_msg:
        response_data = u'%s - %s' % (response_data, extra_msg)
    return _finish(403, response_data, u'json')


def _finish_not_found(extra_msg=None):
    response_data = _(u'Not found')
    if extra_msg:
        response_data = u'%s - %s' % (response_data, extra_msg)
    return _finish(404, response_data, u'json')


def _finish_bad_request(extra_msg=None):
    response_data = _(u'Bad request')
    if extra_msg:
        response_data = u'%s - %s' % (response_data, extra_msg)
    return _finish(400, response_data, u'json')


def _wrap_jsonp(callback, response_msg):
    return u'{0}({1});'.format(callback, response_msg)


def _get_request_data(try_url_params=False):
    u'''Returns a dictionary, extracted from a request.

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
    def mixed(multi_dict):
        u'''Return a dict with values being lists if they have more than one
           item or a string otherwise
        '''
        out = {}
        for key, value in six.iteritems(multi_dict.to_dict(flat=False)):
            out[key] = value[0] if len(value) == 1 else value
        return out

    if not try_url_params and request.method == u'GET':
        raise ValueError(u'Invalid request. Please use POST method '
                         'for your request')

    request_data = {}
    if request.method in [u'POST', u'PUT'] and request.form:
        values = list(request.form.values())
        if (len(values) == 1 and
                values[0] in [u'1', u'']):
            try:
                keys = list(request.form.keys())
                request_data = json.loads(keys[0])
            except ValueError as e:
                raise ValueError(
                    u'Error decoding JSON data. '
                    'Error: %r '
                    'JSON data extracted from the request: %r' %
                    (e, request_data))
        else:
            request_data = mixed(request.form)
    elif request.args and try_url_params:
        request_data = mixed(request.args)
    elif (request.data and request.data != u'' and
          request.content_type != u'multipart/form-data'):
        try:
            request_data = request.get_json()
        except BadRequest as e:
            raise ValueError(u'Error decoding JSON data. '
                             'Error: %r '
                             'JSON data extracted from the request: %r' %
                             (e, request_data))
    if not isinstance(request_data, dict):
        raise ValueError(u'Request data JSON decoded to %r but '
                         'it needs to be a dictionary.' % request_data)

    if request.method == u'PUT' and not request_data:
        raise ValueError(u'Invalid request. Please use the POST method for '
                         'your request')
    for field_name, file_ in six.iteritems(request.files):
        request_data[field_name] = file_
    log.debug(u'Request data extracted: %r', request_data)

    return request_data


def _get_action_from_map(action_map, register, subregister):
    u'''Helper function to get the action function specified in
        the action map'''

    # translate old package calls to use dataset
    if register == u'package':
        register = u'dataset'

    action = action_map.get((register, subregister))
    if not action:
        action = action_map.get(register)
    if action:
        return get_action(action)


# View functions

def action(logic_function, ver=API_DEFAULT_VERSION):
    u'''Main endpoint for the action API (v3)

    Creates a dict with the incoming request data and calls the appropiate
    logic function. Returns a JSON response with the following keys:

        * ``help``: A URL to the docstring for the specified action
        * ``success``: A boolean indicating if the request was successful or
                an exception was raised
        * ``result``: The output of the action, generally an Object or an Array
    '''

    # Check if action exists
    try:
        function = get_action(logic_function)
    except KeyError:
        msg = u'Action name not known: {0}'.format(logic_function)
        log.info(msg)
        return _finish_bad_request(msg)

    context = {u'model': model, u'session': model.Session, u'user': g.user,
               u'api_version': ver, u'auth_user_obj': g.userobj}
    model.Session()._context = context

    return_dict = {u'help': url_for(u'api.action',
                                    logic_function=u'help_show',
                                    ver=ver,
                                    name=logic_function,
                                    _external=True,
                                    )
                   }

    # Get the request data
    try:
        side_effect_free = getattr(function, u'side_effect_free', False)

        request_data = _get_request_data(
            try_url_params=side_effect_free)
    except ValueError as inst:
        log.info(u'Bad Action API request data: %s', inst)
        return _finish_bad_request(
            _(u'JSON Error: %s') % inst)
    if not isinstance(request_data, dict):
        # this occurs if request_data is blank
        log.info(u'Bad Action API request data - not dict: %r',
                 request_data)
        return _finish_bad_request(
            _(u'Bad request data: %s') %
            u'Request data JSON decoded to %r but '
            u'it needs to be a dictionary.' % request_data)
    if u'callback' in request_data:
        del request_data[u'callback']
        g.user = None
        g.userobj = None
        context[u'user'] = None
        context[u'auth_user_obj'] = None

    # Call the action function, catch any exception
    try:
        result = function(context, request_data)
        return_dict[u'success'] = True
        return_dict[u'result'] = result
    except DataError as e:
        log.info(u'Format incorrect (Action API): %s - %s',
                 e.error, request_data)
        return_dict[u'error'] = {u'__type': u'Integrity Error',
                                 u'message': e.error,
                                 u'data': request_data}
        return_dict[u'success'] = False
        return _finish(400, return_dict, content_type=u'json')
    except NotAuthorized as e:
        return_dict[u'error'] = {u'__type': u'Authorization Error',
                                 u'message': _(u'Access denied')}
        return_dict[u'success'] = False

        if text_type(e):
            return_dict[u'error'][u'message'] += u': %s' % e

        return _finish(403, return_dict, content_type=u'json')
    except NotFound as e:
        return_dict[u'error'] = {u'__type': u'Not Found Error',
                                 u'message': _(u'Not found')}
        if text_type(e):
            return_dict[u'error'][u'message'] += u': %s' % e
        return_dict[u'success'] = False
        return _finish(404, return_dict, content_type=u'json')
    except ValidationError as e:
        error_dict = e.error_dict
        error_dict[u'__type'] = u'Validation Error'
        return_dict[u'error'] = error_dict
        return_dict[u'success'] = False
        # CS nasty_string ignore
        log.info(u'Validation error (Action API): %r', str(e.error_dict))
        return _finish(409, return_dict, content_type=u'json')
    except SearchQueryError as e:
        return_dict[u'error'] = {u'__type': u'Search Query Error',
                                 u'message': u'Search Query is invalid: %r' %
                                 e.args}
        return_dict[u'success'] = False
        return _finish(400, return_dict, content_type=u'json')
    except SearchError as e:
        return_dict[u'error'] = {u'__type': u'Search Error',
                                 u'message': u'Search error: %r' % e.args}
        return_dict[u'success'] = False
        return _finish(409, return_dict, content_type=u'json')
    except SearchIndexError as e:
        return_dict[u'error'] = {
            u'__type': u'Search Index Error',
            u'message': u'Unable to add package to search index: %s' %
                       str(e)}
        return_dict[u'success'] = False
        return _finish(500, return_dict, content_type=u'json')
    except Exception as e:
        return_dict[u'error'] = {
            u'__type': u'Internal Server Error',
            u'message': u'Internal Server Error'}
        return_dict[u'success'] = False
        log.exception(e)
        return _finish(500, return_dict, content_type=u'json')

    return _finish_ok(return_dict)


def get_api(ver=1):
    u'''Root endpoint for the API, returns the version number'''

    response_data = {
        u'version': ver
    }
    return _finish_ok(response_data)


def dataset_autocomplete(ver=API_REST_DEFAULT_VERSION):
    q = request.args.get(u'incomplete', u'')
    limit = request.args.get(u'limit', 10)
    package_dicts = []
    if q:
        context = {u'model': model, u'session': model.Session,
                   u'user': g.user, u'auth_user_obj': g.userobj}

        data_dict = {u'q': q, u'limit': limit}

        package_dicts = get_action(
            u'package_autocomplete')(context, data_dict)

    resultSet = {u'ResultSet': {u'Result': package_dicts}}
    return _finish_ok(resultSet)


def tag_autocomplete(ver=API_REST_DEFAULT_VERSION):
    q = request.args.get(u'incomplete', u'')
    limit = request.args.get(u'limit', 10)
    vocab = request.args.get(u'vocabulary_id', u'')
    tag_names = []
    if q:
        context = {u'model': model, u'session': model.Session,
                   u'user': g.user, u'auth_user_obj': g.userobj}

        data_dict = {u'q': q, u'limit': limit}
        if vocab != u'':
            data_dict[u'vocabulary_id'] = vocab

        tag_names = get_action(u'tag_autocomplete')(context, data_dict)

    resultSet = {
        u'ResultSet': {
            u'Result': [{u'Name': tag} for tag in tag_names]
        }
    }
    return _finish_ok(resultSet)


def format_autocomplete(ver=API_REST_DEFAULT_VERSION):
    q = request.args.get(u'incomplete', u'')
    limit = request.args.get(u'limit', 5)
    formats = []
    if q:
        context = {u'model': model, u'session': model.Session,
                   u'user': g.user, u'auth_user_obj': g.userobj}
        data_dict = {u'q': q, u'limit': limit}
        formats = get_action(u'format_autocomplete')(context, data_dict)

    resultSet = {
        u'ResultSet': {
            u'Result': [{u'Format': format} for format in formats]
        }
    }
    return _finish_ok(resultSet)


def user_autocomplete(ver=API_REST_DEFAULT_VERSION):
    q = request.args.get(u'q', u'')
    limit = request.args.get(u'limit', 20)
    ignore_self = request.args.get(u'ignore_self', False)
    user_list = []
    if q:
        context = {u'model': model, u'session': model.Session,
                   u'user': g.user, u'auth_user_obj': g.userobj}

        data_dict = {u'q': q, u'limit': limit, u'ignore_self': ignore_self}

        user_list = get_action(u'user_autocomplete')(context, data_dict)
    return _finish_ok(user_list)


def group_autocomplete(ver=API_REST_DEFAULT_VERSION):
    q = request.args.get(u'q', u'')
    limit = request.args.get(u'limit', 20)
    group_list = []

    if q:
        context = {u'user': g.user, u'model': model}
        data_dict = {u'q': q, u'limit': limit}
        group_list = get_action(u'group_autocomplete')(context, data_dict)
    return _finish_ok(group_list)


def organization_autocomplete(ver=API_REST_DEFAULT_VERSION):
    q = request.args.get(u'q', u'')
    limit = request.args.get(u'limit', 20)
    organization_list = []

    if q:
        context = {u'user': g.user, u'model': model}
        data_dict = {u'q': q, u'limit': limit}
        organization_list = get_action(
            u'organization_autocomplete')(context, data_dict)
    return _finish_ok(organization_list)


def snippet(snippet_path, ver=API_REST_DEFAULT_VERSION):
    u'''Renders and returns a snippet used by ajax calls

        We only allow snippets in templates/ajax_snippets and its subdirs
    '''
    snippet_path = u'ajax_snippets/' + snippet_path
    # werkzeug.datastructures.ImmutableMultiDict.to_dict
    # by default returns flattened dict with first occurences of each key.
    # For retrieving multiple values per key, use named argument `flat`
    # set to `False`
    extra_vars = request.args.to_dict()
    return render(snippet_path, extra_vars=extra_vars)


def i18n_js_translations(lang, ver=API_REST_DEFAULT_VERSION):

    if lang not in get_locales_from_config():
        return _finish_bad_request(u'Unknown locale: {}'.format(lang))

    ckan_path = os.path.join(os.path.dirname(__file__), u'..')
    source = os.path.abspath(os.path.join(ckan_path, u'public',
                             u'base', u'i18n', u'{0}.js'.format(lang)))
    if not os.path.exists(source):
        return u'{}'
    translations = json.load(io.open(source, u'r', encoding=u'utf-8'))
    return _finish_ok(translations)


# Routing

# Root
api.add_url_rule(u'/', view_func=get_api, strict_slashes=False)
api.add_url_rule(u'/<int(min=1, max={0}):ver>'.format(API_MAX_VERSION),
                 view_func=get_api, strict_slashes=False)

# Action API (v3)

api.add_url_rule(u'/action/<logic_function>', methods=[u'GET', u'POST'],
                 view_func=action)
api.add_url_rule(u'/<int(min=3, max={0}):ver>/action/<logic_function>'.format(
                 API_MAX_VERSION),
                 methods=[u'GET', u'POST'],
                 view_func=action)


# Util API

util_rules = [
    (u'/util/dataset/autocomplete', dataset_autocomplete),
    (u'/util/user/autocomplete', user_autocomplete),
    (u'/util/tag/autocomplete', tag_autocomplete),
    (u'/util/group/autocomplete', group_autocomplete),
    (u'/util/organization/autocomplete', organization_autocomplete),
    (u'/util/resource/format_autocomplete', format_autocomplete),
    (u'/util/snippet/<snippet_path>', snippet),
    (u'/i18n/<lang>', i18n_js_translations),
]

version_rule = u'/<int(min=1, max=2):ver>'
for rule, view_func in util_rules:
    api.add_url_rule(rule, view_func=view_func)
    api.add_url_rule(version_rule + rule, view_func=view_func)
