import os
try:
    import json
except ImportError:
    import simplejson as json
from ofs.base import OFSInterface, OFSException
import getpass
import urllib2
import boto
import boto.exception
from boto.connection import AWSAuthConnection
import mimetypes
from hashlib import md5
import base64
from ckanclient import CkanClient

class S3Bounce(OFSInterface):
    """
    Use ckanext-storage API to bounce to an S3 store
    """
    def __init__(self, api_base):
        self.ckan = CkanClient(base_location=api_base)

    def put_stream(self, bucket, label, fp, metadata={}, cb=None, num_cb=None):
        if metadata is None:
            metadata = { "_owner": getpass.getuser()}

        path = "/" + bucket + "/" + label

        content_type = metadata.get("_format", "application/octet-stream")
        
        metadata = self.ckan.storage_metadata_set(path, metadata)
        BufferSize = 65536 ## set to something very small to make sure
                                       ## chunking is working properly

        headers = { 'Content-Type': content_type }

        #if content_type is None:
        #    content_type = mimetypes.guess_type(filename)[0] or "text/plain"
        #headers['Content-Type'] = content_type
        #if content_encoding is not None:
        #   headers['Content-Encoding'] = content_encoding

        m = md5()
        fp.seek(0)
        s = fp.read(BufferSize)
        while s:
            m.update(s)
            s = fp.read(BufferSize)
        self.size = fp.tell()
        fp.seek(0)

        self.md5 = m.hexdigest()
        headers['Content-MD5'] = base64.encodestring(m.digest()).rstrip('\n')
        headers['Content-Length'] = str(self.size)

        headers['Expect'] = '100-Continue'

        host, headers = self.ckan.storage_auth_get(path, headers)

        def sender(http_conn, method, path, data, headers):
            http_conn.putrequest(method, path)
            for key in headers:
                http_conn.putheader(key, headers[key])
            http_conn.endheaders()
            fp.seek(0)
            http_conn.set_debuglevel(0) ### XXX set to e.g. 4 to see what going on
            if cb:
                if num_cb > 2:
                    cb_count = self.size / BufferSize / (num_cb-2)
                elif num_cb < 0:
                    cb_count = -1
                else:
                    cb_count = 0
                i = total_bytes = 0
                cb(total_bytes, self.size)
            l = fp.read(BufferSize)
            while len(l) > 0:
                http_conn.send(l)
                if cb:
                    total_bytes += len(l)
                    i += 1
                    if i == cb_count or cb_count == -1:
                        cb(total_bytes, self.size)
                        i = 0
                l = fp.read(BufferSize)
            if cb:
                cb(total_bytes, self.size)
            response = http_conn.getresponse()
            body = response.read()
            fp.seek(0)
            if response.status == 500 or response.status == 503 or \
                    response.getheader('location'):
                # we'll try again
                return response
            elif response.status >= 200 and response.status <= 299:
                self.etag = response.getheader('etag')
                if self.etag != '"%s"'  % self.md5:
                    raise Exception('ETag from S3 did not match computed MD5')
                return response
            else:
                #raise provider.storage_response_error(
                #    response.status, response.reason, body)
                raise Exception(response.status, response.reason, body)

        awsc = AWSAuthConnection(host,
                                 aws_access_key_id="key_id",
                                 aws_secret_access_key="secret")
                                 
        awsc._mexe('PUT', path, None, headers, sender=sender)

        metadata = self.ckan.storage_metadata_update(path, {})
        from pprint import pprint
        pprint(metadata)
