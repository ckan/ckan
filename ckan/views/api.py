# encoding: utf-8

import cgi
import logging

from flask import Blueprint, request, make_response, g, url_for
from werkzeug.exceptions import BadRequest

import ckan.model as model
from ckan.common import json, _

from ckan.lib.navl.dictization_functions import DataError
from ckan.logic import get_action, ValidationError, NotFound, NotAuthorized
from ckan.lib.search import SearchError, SearchIndexError, SearchQueryError


log = logging.getLogger(__name__)

CONTENT_TYPES = {
    u'text': u'text/plain;charset=utf-8',
    u'html': u'text/html;charset=utf-8',
    u'json': u'application/json;charset=utf-8',
}


API_DEFAULT_VERSION = 3
API_MAX_VERSION = 3


# Blueprint definition

api = Blueprint(u'api', __name__, url_prefix=u'/api')


# Private methods


def _finish(status_int, response_data=None,
            content_type=u'text', headers=None):
    u'''When a controller method has completed, call this method
    to prepare the response.
    @return response message - return this value from the controller
                               method
             e.g. return _finish(404, 'Package not found')
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
        # Support "JSONP" callback.
        if (status_int == 200 and u'callback' in request.args and
                request.method == u'GET'):
            # escape callback to remove '<', '&', '>' chars
            callback = cgi.escape(request.args[u'callback'])
            response_msg = _wrap_jsonp(callback, response_msg)
    return make_response((response_msg, status_int, headers))


def _finish_ok(response_data=None,
               content_type=u'json',
               resource_location=None):
    u'''If a controller method has completed successfully then
    calling this method will prepare the response.
    @param resource_location - specify this if a new
       resource has just been created.
    @return response message - return this value from the controller
                               method
                               e.g. return _finish_ok(pkg_dict)
    '''
    status_int = 200
    headers = None
    if resource_location:
        status_int = 201
        try:
            resource_location = str(resource_location)
        except Exception, inst:
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
    return u'%s(%s);' % (callback, response_msg)


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
    def make_unicode(entity):
        u'''Cast bare strings and strings in lists or dicts to Unicode. '''
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
        u'''Return a dict with values being lists if they have more than one
           item or a string otherwise
        '''
        out = {}
        for key, value in multi_dict.to_dict(flat=False).iteritems():
            out[key] = value[0] if len(value) == 1 else value
        return out

    if not try_url_params and request.method == u'GET':
        raise ValueError(u'Invalid request. Please use POST method '
                         'for your request')

    request_data = {}
    if request.method == u'POST' and request.form:
        if (len(request.form.values()) == 1 and
                request.form.values()[0] in [u'1', u'']):
            try:
                request_data = json.loads(request.form.keys()[0])
            except ValueError, e:
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
        except BadRequest, e:
            raise ValueError(u'Error decoding JSON data. '
                             'Error: %r '
                             'JSON data extracted from the request: %r' %
                             (e, request_data))
    if not isinstance(request_data, dict):
        raise ValueError(u'Request data JSON decoded to %r but '
                         'it needs to be a dictionary.' % request_data)
    if request_data:
        # ensure unicode values
        for key, val in request_data.items():
            # if val is str then assume it is ascii, since json converts
            # utf8 encoded JSON to unicode
            request_data[key] = make_unicode(val)
    log.debug(u'Request data extracted: %r', request_data)
    return request_data


# View functions

def action(logic_function, ver=API_DEFAULT_VERSION):

    try:
        function = get_action(logic_function)
    except KeyError:
        msg = u'Action name not known: {0}'.format(logic_function)
        log.info(msg)
        return _finish_bad_request(msg)

    context = {u'model': model, u'session': model.Session, u'user': g.user,
               u'api_version': ver, u'auth_user_obj': g.userobj}
    model.Session()._context = context

    # TODO: backwards-compatible named routes?
    return_dict = {u'help': url_for(u'api.action',
                                    logic_function=u'help_show',
                                    ver=ver,
                                    name=logic_function,
                                    _external=True,
                                    )
                   }
    try:
        side_effect_free = getattr(function, u'side_effect_free', False)

        request_data = _get_request_data(
            try_url_params=side_effect_free)
    except ValueError, inst:
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

    # if callback is specified we do not want to send that to the search
    if u'callback' in request_data:
        del request_data[u'callback']
        g.user = None
        g.userobj = None
        context[u'user'] = None
        context[u'auth_user_obj'] = None
    try:
        result = function(context, request_data)
        return_dict[u'success'] = True
        return_dict[u'result'] = result
    except DataError, e:
        log.info(u'Format incorrect (Action API): %s - %s',
                 e.error, request_data)
        return_dict[u'error'] = {u'__type': u'Integrity Error',
                                 u'message': e.error,
                                 u'data': request_data}
        return_dict[u'success'] = False
        return _finish(400, return_dict, content_type=u'json')
    except NotAuthorized, e:
        return_dict[u'error'] = {u'__type': u'Authorization Error',
                                 u'message': _(u'Access denied')}
        return_dict[u'success'] = False

        if unicode(e):
            return_dict[u'error'][u'message'] += u': %s' % e

        return _finish(403, return_dict, content_type=u'json')
    except NotFound, e:
        return_dict[u'error'] = {u'__type': u'Not Found Error',
                                 u'message': _(u'Not found')}
        if unicode(e):
            return_dict[u'error'][u'message'] += u': %s' % e
        return_dict[u'success'] = False
        return _finish(404, return_dict, content_type=u'json')
    except ValidationError, e:
        error_dict = e.error_dict
        error_dict[u'__type'] = u'Validation Error'
        return_dict[u'error'] = error_dict
        return_dict[u'success'] = False
        # CS nasty_string ignore
        log.info(u'Validation error (Action API): %r', str(e.error_dict))
        return _finish(409, return_dict, content_type=u'json')
    except SearchQueryError, e:
        return_dict[u'error'] = {u'__type': u'Search Query Error',
                                 u'message': u'Search Query is invalid: %r' %
                                 e.args}
        return_dict[u'success'] = False
        return _finish(400, return_dict, content_type=u'json')
    except SearchError, e:
        return_dict[u'error'] = {u'__type': u'Search Error',
                                 u'message': u'Search error: %r' % e.args}
        return_dict[u'success'] = False
        return _finish(409, return_dict, content_type=u'json')
    except SearchIndexError, e:
        return_dict[u'error'] = {
            u'__type': u'Search Index Error',
            u'message': u'Unable to add package to search index: %s' %
                       str(e)}
        return_dict[u'success'] = False
        return _finish(500, return_dict, content_type=u'json')
    return _finish_ok(return_dict)


def get_api(ver=1):
    response_data = {
        u'version': ver
    }
    return _finish_ok(response_data)


# Routing


api.add_url_rule(u'/', view_func=get_api, strict_slashes=False)
api.add_url_rule(u'/action/<logic_function>', methods=[u'GET', u'POST'],
                 view_func=action)
api.add_url_rule(u'/<int(min=3, max={0}):ver>/action/<logic_function>'.format(
                 API_MAX_VERSION),
                 methods=[u'GET', u'POST'],
                 view_func=action)
