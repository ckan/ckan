# encoding: utf-8

import decorator

from ckan.common import json, request, response


def to_jsonp(data):
    content_type = 'application/json;charset=utf-8'
    result = json.dumps(data, sort_keys=True)
    if 'callback' in request.params:
        response.headers['Content-Type'] = content_type
        cbname = request.params['callback']
        result = '%s(%s);' % (cbname, result)
    else:
        response.headers['Content-Type'] = content_type
    return result


def jsonpify(func, *args, **kwargs):
    """A decorator that reformats the output as JSON; or, if the
    *callback* parameter is specified (in the HTTP request), as JSONP.
    
    Very much modelled after pylons.decorators.jsonify .
    """
    data = func(*args, **kwargs)
    return to_jsonp(data)

jsonpify = decorator.decorator(jsonpify)

