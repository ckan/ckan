'''This implements OFS backends for remote storage systems supported by the
`Boto library <http://code.google.com/p/boto/`_ including S3 and archive.org.

Boto will also be the reference implementation for Google Storage, so only minor
modifications would be required to support both GS and S3 through this module.
'''
import os
try:
    import json
except ImportError:
    import simplejson as json
from datetime import datetime
from tempfile import mkstemp
from ofs.base import OFSInterface, OFSException
import boto
import boto.exception
import boto.connection
import boto.s3.connection

CALLING_FORMATS = {
    'SubdomainCallingFormat': boto.s3.connection.SubdomainCallingFormat(),
    'VHostCallingFormat': boto.s3.connection.VHostCallingFormat(),
    'OrdinaryCallingFormat': boto.s3.connection.OrdinaryCallingFormat(),
    'ProtocolIndependentOrdinaryCallingFormat': boto.s3.connection.ProtocolIndependentOrdinaryCallingFormat()}


class BotoOFS(OFSInterface):
    '''s3 backend for OFS.
    
    This is a simple S3 implementation of OFS that depends on the boto library.
    '''
    
    def __init__(self, conn):
        self.conn = conn
        self._bucket_cache = {}
    
    def _get_bucket(self, bucket_name):
        if not bucket_name in self._bucket_cache.keys():
            self._bucket_cache[bucket_name] = self.conn.lookup(bucket_name)
        return self._bucket_cache[bucket_name]
    
    def _require_bucket(self, bucket_name):
        """ Also try to create the bucket. """
        if not self.exists(bucket_name) and not self.claim_bucket(bucket_name):
            raise OFSException("Invalid bucket: %s" % bucket_name)
        return self._get_bucket(bucket_name)
        
    def _get_key(self, bucket, label):
        return bucket.get_key(label)
    
    def _require_key(self, bucket, label):
        key = self._get_key(bucket, label)
        if key is None:
            raise OFSException("%s->%s does not exist!" % (bucket.name, label))
        return key
    
    def exists(self, bucket, label=None):
        bucket = self._get_bucket(bucket)
        if bucket is None: 
            return False
        return (label is None) or (label in bucket)
    
    def claim_bucket(self, bucket):
        try:
            if self.exists(bucket):
                return False
            self._bucket_cache[bucket] = self.conn.create_bucket(bucket)
            return True
        except boto.exception.S3CreateError, sce:
            return False
    
    def _del_bucket(self, bucket):
        if self.exists(bucket):
            bucket = self._get_bucket(bucket)
            for key in bucket.get_all_keys():
                key.delete()
            bucket.delete()
            del self._bucket_cache[bucket.name]
    
    def list_labels(self, bucket):
        _bucket = self._get_bucket(bucket)
        for key in _bucket.list():
            yield key.name

    def list_buckets(self):
        for bucket in self.conn.get_all_buckets():
            self._bucket_cache[bucket.name] = bucket
            yield bucket.name

    def get_stream(self, bucket, label, as_stream=True):
        bucket = self._require_bucket(bucket)
        key = self._require_key(bucket, label)
        if not as_stream:
            return key.get_contents_as_string()
        return key
    
    def get_url(self, bucket, label):
        bucket = self._require_bucket(bucket)
        key = self._require_key(bucket, label)
        key.make_public()
        # expire can be negative when data is public
        return key.generate_url(-1) 

    def put_stream(self, bucket, label, stream_object, params={}):
        bucket = self._require_bucket(bucket)
        key = self._get_key(bucket, label)
        if key is None:
            key = bucket.new_key(label)
            if not '_creation_time' in params:
                params['_creation_time'] = str(datetime.utcnow())
        
        if not '_checksum' in params:
            params['_checksum'] = 'md5:' + key.compute_md5(stream_object)[0]
        
        self._update_key_metadata(key, params)
        key.set_contents_from_file(stream_object)
        key.close()

    def del_stream(self, bucket, label):
        """ Will fail if the bucket or label don't exist """
        bucket = self._require_bucket(bucket)
        key = self._require_key(bucket, label)
        key.delete()

    def get_metadata(self, bucket, label):
        bucket = self._require_bucket(bucket)
        key = self._require_key(bucket, label)
        
        meta = dict(key.metadata)
        meta.update({
            '_bucket': bucket.name,
            '_label': label,
            '_owner': key.owner,
            '_last_modified': key.last_modified,
            '_format': key.content_type,
            '_content_length': key.size,
            # Content-MD5 header is not made available from boto it seems but
            # etag is and it corresponds to MD5. See
            # http://code.google.com/apis/storage/docs/reference-headers.html#etag
            # https://github.com/boto/boto/blob/master/boto/s3/key.py#L531
            '_checksum': 'md5:' + key.etag.strip('"')
        })
        return meta
    
    def _update_key_metadata(self, key, params):
        if '_format' in params:
            key.content_type = params['_format']
            del params['_format']
        
        if '_owner' in params:
            key.owner = params['_owner']
            del params['_owner']
        for name in ['_label', '_bucket', '_last_modified', '_content_length']:
            if name in params:
                del params[name]
        key.update_metadata(params)

    def update_metadata(self, bucket, label, params):
        key = self._require_key(self._require_bucket(bucket), label)
        self._update_key_metadata(key, params)
        # cannot update metadata on its own. way round this is to copy file
        key.copy(key.bucket, key.name, dict(key.metadata), preserve_acl=True)
        key.close()
    
    def del_metadata_keys(self, bucket, label, keys):
        key = self._require_key(self._require_bucket(bucket), label)
        for _key, value in key.metadata.items():
            if _key in keys:
                del key.metadata[_key] 
        key.close()

    def authenticate_request(self, method, bucket='', key='', headers=None):
        '''Authenticate a HTTP request by filling in Authorization field header.

        :param method: HTTP method (e.g. GET, PUT, POST)
        :param bucket: name of the bucket.
        :param key: name of key within bucket.
        :param headers: dictionary of additional HTTP headers.

        :return: boto.connection.HTTPRequest object with Authorization header
        filled (NB: will also have a Date field if none before and a User-Agent
        field will be set to Boto).
        '''
        # following is extracted from S3Connection.make_request and the method
        # it calls: AWSAuthConnection.make_request
        path = self.conn.calling_format.build_path_base(bucket, key)
        auth_path = self.conn.calling_format.build_auth_path(bucket, key)
        http_request = boto.connection.AWSAuthConnection.build_base_http_request(
                self.conn,
                method,
                path,
                auth_path,
                {},
                headers
                )
        http_request.authorize(connection=self.conn)
        return http_request


class S3OFS(BotoOFS):
    
    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None, **kwargs):
        # assume external configuration at the moment. 
        # http://code.google.com/p/boto/wiki/BotoConfig
        if 'calling_format' in kwargs:
            kwargs['calling_format'] = CALLING_FORMATS[kwargs['calling_format']]
        conn = boto.connect_s3(aws_access_key_id, aws_secret_access_key, **kwargs)
        super(S3OFS, self).__init__(conn)


class GSOFS(BotoOFS):
    '''Google storage OFS backend.
    '''

    def __init__(self, gs_access_key_id=None, gs_secret_access_key=None, **kwargs):
        conn = boto.connect_gs(gs_access_key_id, gs_secret_access_key, **kwargs)
        super(GSOFS, self).__init__(conn)    

class ArchiveOrgOFS(S3OFS):
    '''An archive.org backend utilizing the archive.org s3 interface (see:
    http://www.archive.org/help/abouts3.txt).

    '''

    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None, **kwargs):
        super(ArchiveOrgOFS, self).__init__(aws_access_key_id, aws_secret_access_key,
            host="s3.us.archive.org", **kwargs)
