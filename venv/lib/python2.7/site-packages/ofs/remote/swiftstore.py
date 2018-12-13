'''This implements OFS backends for remote storage systems supported by the
`python-swiftclient <https://github.com/openstack/python-swiftclient>`_ .

'''
import os
try:
    import json
except ImportError:
    import simplejson as json
import logging

from datetime import datetime
from tempfile import mkstemp
from ofs.base import OFSInterface, OFSException

import swiftclient
from swiftclient import client

SWIFT_AUTH_VERSION = 2
CHUNK_SIZE = 1024
PUBLIC_HEADER = {"X-Container-Read": ".r:*"}

class SwiftOFS(OFSInterface):
    '''swift backend for OFS.
    
    This is a simple implementation of OFS for controll OpenStack Swift.
    There are some difference in term of storage.
    1. bucket = container in swift
    2. label = object in swift
    '''
    def __init__(self, os_auth_url=None, os_user=None,
                       os_passwd=None, os_tenant=None):
        # Currently support keystone authentication.
        self.connection = client.Connection(authurl=os_auth_url,
                                            user=os_user,
                                            key=os_passwd,
                                            tenant_name=os_tenant,
                                            auth_version=SWIFT_AUTH_VERSION)

    def _get_object(self, container, obj, chunk_size=0):
        try:
            if chunk_size > 0:
                return None, self.ChunkedStream(self.connection, container, obj, chunk_size)
            return self.connection.get_object(container, obj, resp_chunk_size=chunk_size)
        except swiftclient.ClientException as e:
            logging.error(e)
            return None, None

    def _get_container(self, container):
        try: 
            return self.connection.get_container(container)
        except swiftclient.ClientException as e:
            logging.error(e)
            return None

    def _head_container(self, container):
        try:
            return self.connection.head_container(container)
        except swiftclient.ClientException as e:
            logging.error(e)
            return None

    def _head_object(self, container, obj):
        try:        
            return self.connection.head_object(container, obj)
        except swiftclient.ClientException as e:
            logging.error(e)
            return None

    def _convert_to_meta(self, params):
        meta = dict()
        for k in params:
            meta.update({'X-Object-Meta-%s' % k: params[k]}) 
        return meta

    def exists(self, bucket, label=None):
        container = self._head_container(bucket)
        if container is None: 
            return False
        return (label is None) or (self._head_object(bucket, label) is not None)
    
    def claim_bucket(self, bucket):
        try:
            if not self._get_container(bucket):
                self.connection.put_container(bucket, headers=PUBLIC_HEADER)
                return True
            return False
        except swiftclient.ClientException as e:
            return False
    
    def list_labels(self, bucket):
        _, labels = self._get_container(bucket)
        for label in labels:
            yield label['name']

    def list_buckets(self):
        # blank string to container name means list buckets
        _, buckets = self._get_container('')
        for bucket in buckets:
            yield bucket['name']

    def get_stream(self, bucket, label, as_stream=True):
        if not self.exists(bucket, label):
            raise OFSException("Unable to get stream: bucket=%s, label=%s" % (bucket, label))
        if not as_stream:
            _, body = self._get_object(bucket, label)
            return body
        _, body = self._get_object(bucket, label, chunk_size=CHUNK_SIZE)
        return body
    
    def get_url(self, bucket, label):
        container = self._head_container(bucket)
        obj = self._head_object(bucket, label)
        return "%s/%s/%s" % (self.connection.url, bucket, label)

    def put_stream(self, bucket, label, stream_object, params={}):
        ''' Create a new file to swift object storage. '''
        self.claim_bucket(bucket) 
        self.connection.put_object(bucket, label, stream_object,
                                   headers=self._convert_to_meta(params))

    def del_stream(self, bucket, label):
        self.connection.delete_object(bucket, label)

    def get_metadata(self, bucket, label):
        container = self._head_container(bucket)
        obj = self._head_object(bucket, label)
        meta = dict()
        meta.update({
            '_bucket': bucket,
            '_label': label,
            '_owner': bucket,
            '_last_modified': obj['last-modified'],
            '_format': obj['content-type'],
            '_content_length': obj['content-length'],
            '_checksum': obj['etag'],
            '_creation_time': obj['x-timestamp']
        })
        for k in obj:
            if k.startswith('x-object-meta-'):
                meta.update({k.lstrip('x-object-meta-'): obj[k]})
        return meta
    
    def update_metadata(self, bucket, label, params):
        container = self._head_container(bucket)
        obj = self._head_object(bucket, label)
        self.connection.post_object(bucket, label, self._convert_to_meta(params))
    
    def del_metadata_keys(self, bucket, label, keys):
        key = self._require_key(self._require_bucket(bucket), label)
        for _key, value in key.metadata.items():
            if _key in keys:
                del key.metadata[_key] 
        key.close()

    class ChunkedStream(object):
        ''' Simple stream handler '''
        def __init__(self, connection, container, obj, chunk):
            self.connection = connection
            self.container = container
            self.obj = obj
            self.chunk = chunk

        def read(self):
            ''' Swift returned a genertor if chunk size specified. '''
            _, body = self.connection.get_object(self.container,
                                                 self.obj,
                                                 resp_chunk_size=self.chunk)
            return body.next()

