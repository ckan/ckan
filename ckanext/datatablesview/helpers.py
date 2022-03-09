from urllib import quote, unquote
from cgi import escape

from ckan.plugins.toolkit import request

def encode_uri_deep(_value):
    return escape(quote(_value.encode('utf-8')).encode('ascii'))

def decode_uri_deep(_value):
    return unquote(str(_value))

def get_filters(encode=False,decode=False):
    if 'filters' not in request.params:
        return ''
    if encode:
        return encode_uri_deep(request.params['filters'])
    elif decode:
        return decode_uri_deep(request.params['filters'])
    return request.params['filters']