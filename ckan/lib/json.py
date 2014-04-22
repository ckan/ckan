import re
import datetime
from ckan.lib.helpers import json as j

class DateTimeJsonEncoder(j.JSONEncoder):
    """ Makes sure that the json.dumps() call can handle datetime.datetime objects
        by serialising them to a string """
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        return j.JSONEncoder.default(self, obj)


class DateTimeJsonDecoder(j.JSONDecoder):
    # ISO8601 regex.
    dt = re.compile("^(-?(?:[1-9][0-9]*)?[0-9]{4})-(1[0-2]|0[1-9])-(3[0-1]|0[1-9]"
        "|[1-2][0-9])?T(2[0-3]|[0-1][0-9]):([0-5][0-9]):([0-5][0-9])(\.[0-9]+)??(Z|[+-]"
        "(?:2[0-3]|[0-1][0-9]):[0-5][0-9])?$")

    def __init__(self,*args,**kwargs):
        j.JSONDecoder.__init__(self, object_hook=self.dict_to_object,*args,**kwargs)

    def dict_to_object(self, d):
        import dateutil.parser
        for k, v in d.iteritems():
            if isinstance(v, basestring):
                if DateTimeJsonDecoder.dt.match(v):
                    d[k] = dateutil.parser.parse(v)
        return d
