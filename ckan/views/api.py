# encoding: utf-8

import cgi
import logging

from flask import Blueprint, request, make_response

from ckan.common import json


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


def _wrap_jsonp(callback, response_msg):
    return u'{0}({1});'.format(callback, response_msg)


# View functions

def get_api(ver=1):
    response_data = {
        u'version': ver
    }
    return _finish_ok(response_data)


# Routing
api.add_url_rule(u'/', view_func=get_api, strict_slashes=False)
api.add_url_rule(u'/<int(min=1, max={0}):ver>'.format(API_MAX_VERSION),
                 view_func=get_api, strict_slashes=False)
