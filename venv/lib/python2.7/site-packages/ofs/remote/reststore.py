import os
try:
    import json
except ImportError:
    import simplejson as json
from datetime import datetime
from tempfile import mkstemp
from urllib2 import Request, urlopen, HTTPError
from urllib import urlencode
from urlparse import urljoin
from ofs.base import OFSInterface, OFSException

BOUNDARY = '----------gc0p4Jq0M2Yt08jU534c0p_$'

class MethodRequest(Request):
    
    def get_method(self):
        return self._method

DEFAULT_HOST = 'http://repo.ckan.net'

class RESTOFS(OFSInterface):
    '''OFS interface to a RESTful storage system.'''
    
    def __init__(self, host=DEFAULT_HOST, http_user=None, http_pass=None):
        self.host = host.rstrip('/')
        self.http_user = http_user
        self.http_pass = http_pass
    
    def _multipart_encode(self, data, stream, label, content_type):
        body = []
        for (key, value) in data.items():
            body.append('--' + BOUNDARY)
            body.append('Content-Disposition: form-data; name="%s"' % key)
            body.append('')
            body.append(value)
        body.append('--' + BOUNDARY)
        body.append('Content-Disposition: form-data; name="stream"; filename="%s"' % label)
        body.append('Content-Type: %s' % content_type)
        body.append('Content-Transfer-Encoding: binary')
        body.append('')
        body.append(stream.read())
        body.append('--' + BOUNDARY + '--')
        body.append('')
        body = '\r\n'.join([t for t in body])
        content_type = 'multipart/form-data; boundary=%s' % BOUNDARY
        return content_type, body
        
    def _request(self, path, data=None, headers={}, method='GET'):
        http_headers = {}
        if data is not None and not isinstance(data, basestring):
            data = urlencode(data)
        if headers:
            http_headers.update(headers)
        if self.http_user and self.http_pass:
            http_auth = self.http_user + ':' + self.http_pass
            http_auth = 'Basic ' + http_auth.encode('base64').strip()
            http_headers['Authorization'] = http_auth
        if path.startswith('/'):
            path = urljoin(self.host, path)
        try:
            req = MethodRequest(path, data, headers)
            req._method = method
            return urlopen(req)
        except HTTPError, he:
            return he
        
        
    def _request_json(self, path, data=None, headers={}, method='GET'):
        hdr = {'Accept': 'application/json',
               'Content-Type': 'application/json'}
        hdr.update(headers)
        if data is None:
            data = {} 
        data = json.dumps(data) 
        urlfp = self._request(path, data=data, headers=hdr, method=method)
        try:
            ret_data = urlfp.read()
            try:
                ret_data = json.loads(ret_data)
            except ValueError:
                raise OFSException(urlfp.msg)
            if isinstance(ret_data, dict) and 'error' in ret_data.keys():
                raise OFSException(ret_data.get('message'))
            return ret_data
        finally:
            urlfp.close()
            
    def _del_bucket(self, bucket):
        urlfp = self._request('/' + bucket, method='DELETE')
        return urlfp.code < 400
    
    def exists(self, bucket, label=None):
        path = '/' + bucket
        if label is not None:
            path += '/' + label
        urlfp = self._request(path, method='GET')
        return urlfp.code < 400
    
    def claim_bucket(self, bucket):
        if self.exists(bucket):
            return False
        try:
            self._request_json('/', data={'bucket': bucket}, method='POST')
            return True
        except OFSException, ofse:
            return False
    
    def list_labels(self, bucket):
        labels = self._request_json('/' + bucket)
        return labels.keys()
    
    def list_buckets(self):
        buckets = self._request_json('/')
        return buckets.keys()
    
    def get_stream(self, bucket, label, as_stream=True):
        urlfp = self._request('/' + bucket + '/' + label)
        if urlfp.code >= 400:
            raise OFSException(urlfp.read())
        if not as_stream:
            return urlfp.read()
        return urlfp
        
    def get_url(self, bucket, label):
        urlfp = self._request('/' + bucket + '/' + label)
        return urlfp.url
    
    def put_stream(self, bucket, label, stream_object, params={}):
        content_type = params.get('_format', 'application/octet-stream')
        params['_label'] = label
        params['_bucket'] = bucket
        content_type, body = self._multipart_encode(params, stream_object, 
                                                    label, content_type)
        headers = {'Accept': 'application/json', 
                   'Content-Type': content_type}
        if self.exists(bucket, label):
            urlfp = self._request('/' + bucket + '/' + label, data=body, 
                                  headers=headers, method='PUT')
        else:
            urlfp = self._request('/' + bucket, data=body, 
                                  headers=headers, method='POST')
        try:
            ret_data = json.loads(urlfp.read())
        except ValueError:
            raise OFSException(urlfp.msg)
        if 'error' in ret_data.keys():
            raise OFSException(ret_data.get('message'))
        
    def del_stream(self, bucket, label):
        """ Will fail if the bucket or label don't exist """
        self._request('/' + bucket + '/' + label, method='DELETE')

    def get_metadata(self, bucket, label):
        return self._request_json('/' + bucket + '/' + label + '/meta', method='GET')
    
    def update_metadata(self, bucket, label, params):
        return self._request_json('/' + bucket + '/' + label + '/meta', 
                                  data=params, method='PUT')
    
    def del_metadata_keys(self, bucket, label, keys):
        meta = self.get_metadata(bucket, label)
        for _key, value in meta.items():
            if _key in keys:
                del meta[_key] 
        self.update_metadata(bucket, label, meta)
 
        
