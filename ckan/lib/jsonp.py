import decorator
import datetime
import re
from pylons import request, response

from ckan.lib.helpers import json

class DateTimeJsonEncoder(json.JSONEncoder):
    """ Makes sure that the json.dumps() call can handle datetime.datetime objects
        by serialising them to a string """
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        return json.JSONEncoder.default(self, obj)


class DateTimeJsonDecoder(json.JSONDecoder):
    # ISO8601 regex.
    dt = re.compile("^(-?(?:[1-9][0-9]*)?[0-9]{4})-(1[0-2]|0[1-9])-(3[0-1]|0[1-9]"
        "|[1-2][0-9])?T(2[0-3]|[0-1][0-9]):([0-5][0-9]):([0-5][0-9])(\.[0-9]+)??(Z|[+-]"
        "(?:2[0-3]|[0-1][0-9]):[0-5][0-9])?$")

    def __init__(self,*args,**kwargs):
        json.JSONDecoder.__init__(self, object_hook=self.dict_to_object,*args,**kwargs)

    def dict_to_object(self, d):
        import dateutil.parser
        for k, v in d.iteritems():
            if isinstance(v, unicode):
                if DateTimeJsonDecoder.dt.match(v):
                    d[k] = dateutil.parser.parse(v)
        return d


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

