from urllib.parse import quote, unquote
from cgi import escape

from ckan.plugins.toolkit import request

def encode_datatables_request_filters():
    if 'filters' not in request.params:
        return ''
    return escape(quote(str(request.params['filters'].encode('utf-8')).encode('ascii')))

def decode_datatables_request_filters():
    if 'filters' not in request.params:
        return ''
    return unquote(str(request.params['filters']))