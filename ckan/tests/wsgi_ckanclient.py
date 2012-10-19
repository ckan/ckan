import urllib

import paste.fixture

from ckanclient import CkanClient, CkanApiError
try:
    from ckanclient import ApiRequest
except ImportError:
    # older versions of ckanclient
    from ckanclient import Request as ApiRequest

__all__ = ['WsgiCkanClient', 'ClientError']

__version__ = '0.5'

class ClientError(Exception):
    pass

class WsgiCkanClient(CkanClient):
    '''Same as CkanClient, but instead of requests going through urllib,
    they are passed directly to an application\'s Paste (webtest/wsgi)
    interface.'''
    def __init__(self, app, **kwargs):
        self.app = app
        super(WsgiCkanClient, self).__init__(**kwargs)

    def open_url(self, location, data=None, headers={}, method=None):
        if self.is_verbose:
            self._print("ckanclient: Opening %s" % location)
        self.last_location = location

        if data != None:
            data = urllib.urlencode({data: 1})
        # Don't use request beyond getting the method
        req = ApiRequest(location, data, headers, method=method)

        # Make header values ascii strings
        for key, value in headers.items():
            headers[key] = str('%s' % value)

        method = req.get_method()
        kwargs = {'status':'*', 'headers':headers}
        try:
            if method == 'GET':
                assert not data
                res = self.app.get(location, **kwargs)
            elif method == 'POST':
                res = self.app.post(location, data, **kwargs)
            elif method == 'PUT':
                res = self.app.put(location, data, **kwargs)
            elif method == 'DELETE':
                assert not data
                res = self.app.delete(location, **kwargs)
            else:
                raise ClientError('No Paste interface for method \'%s\': %s' % \
                                  (method, location))
        except paste.fixture.AppError, inst:
            self._print("ckanclient: error: %s" % inst)
            self.last_http_error = inst
            self.last_status = 500
            self.last_message = repr(inst.args)
        else:
            if res.status not in (200, 201):
                self._print("ckanclient: Received HTTP error code from CKAN resource.")
                self._print("ckanclient: location: %s" % location)
                self._print("ckanclient: response code: %s" % res.status)
                self._print("ckanclient: request headers: %s" % headers)
                self._print("ckanclient: request data: %s" % data)
                self._print("ckanclient: error: %s" % res)
                self.last_http_error = res
                self.last_status = res.status
                self.last_message = res.body
            else:
                self._print("ckanclient: OK opening CKAN resource: %s" % location)
                self.last_status = res.status
                self._print('ckanclient: last status %s' % self.last_status)
                self.last_body = res.body
                self._print('ckanclient: last body %s' % self.last_body)
                self.last_headers = dict(res.headers)
                self._print('ckanclient: last headers %s' % self.last_headers)
                content_type = self.last_headers['Content-Type']
                self._print('ckanclient: content type: %s' % content_type)
                is_json_response = False
                if 'json' in content_type:
                    is_json_response = True
                if is_json_response:
                    self.last_message = self._loadstr(self.last_body)
                else:
                    self.last_message = self.last_body
                self._print('ckanclient: last message %s' % self.last_message)
        if self.last_status not in (200, 201):
            raise CkanApiError(self.last_message)

        
