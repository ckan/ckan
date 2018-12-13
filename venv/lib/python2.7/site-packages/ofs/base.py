class OFSException(Exception): pass

class BucketExists(OFSException): pass

class OFSFileNotFound(OFSException): pass

class OFSInterface(object):
    '''Abstract specification of OFS interface. Implementing backends *must*
    implement at least this interface.

    **Metadata**

    Metadata keys must be ascii and alphanumeric plus '_' and '-'.

    Standard metadata: This metadata will always be available from
    get_metadata. Attempts to delete these keys will fail.

        * _creation_date
        * _last_modified
        * _content_length
        * _checksum --> "{type}:{number}" eg "md5:767f7a..."
        * _owner
        * _format (content-type)
        * _bucket
        * _label
    '''
    def exists(bucket, label):
        '''Whether a given bucket:label object already exists.

        :return: bool.
        '''
        raise NotImplementedError

    def claim_bucket(self, bucket):
        '''Claim a bucket.

        :return: True if successful, False otherwise.
        '''
        raise NotImplementedError

    def list_labels(self, bucket):
        '''List labels for the given bucket.

        :param bucket: bucket to list labels for.
        :return: iterator for the labels in the specified bucket.
        '''
        raise NotImplementedError
    
    def list_buckets(self):
        '''List all buckets managed by this OFS instance.
        
        :return: iterator for the buckets.
        '''
        raise NotImplementedError

    def get_stream(self, bucket, label, as_stream=True):
        '''Get a bitstream for the given bucket:label combination.

        :param bucket: the bucket to use.
        :return: bitstream as a file-like object 
        '''
        raise NotImplementedError

    def get_url(self, bucket, label):
        '''Get a URL that should point at the bucket:labelled resource. Aimed to aid web apps by allowing them to redirect to an open resource, rather than proxy the bitstream.

        :param bucket: the bucket to use.
        :param label: the label of the resource to get
        :return: a string URL - NB 'file:///...' is a resource on the locally mounted systems.
        '''
        raise NotImplementedError

    def put_stream(self, bucket, label, stream_object, params={}):
        '''Put a bitstream (stream_object) for the specified bucket:label identifier.

        :param bucket: as standard
        :param label: as standard
        :param stream_object: file-like object to read from.
        :param params: update metadata with these params (see `update_metadata`)
        '''
        raise NotImplementedError

    def del_stream(self, bucket, label):
        '''Delete a bitstream.
        '''
        raise NotImplementedError

    def get_metadata(self, bucket, label):
        '''Get the metadata for this bucket:label identifier.
        '''
        raise NotImplementedError

    def update_metadata(self, bucket, label, params):
        '''Update the metadata with the provided dictionary of params.

        :param parmams: dictionary of key values (json serializable).
        '''
        raise NotImplementedError

    def del_metadata_keys(self, bucket, label, keys):
        '''Delete the metadata corresponding to the specified keys.
        '''
        raise NotImplementedError

