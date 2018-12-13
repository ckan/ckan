from ofs.base import OFSInterface

class LocalFileOFS(OFSInterface):
    '''The simplest possible store you could imagine.

    WARNING: not yet implemented (help wanted!).
    '''
    def __init__(self, storage_dir='ofsdata'):
        self.storage_dir = storage_dir

    def _path(self, bucket, label):
        return os.path.join(self.storage_dir, bucket, label)

    def exists(bucket, label):
        raise NotImplementedError

    def claim_bucket(self, bucket):
        raise NotImplementedError

    def list_labels(self, bucket):
        raise NotImplementedError
    
    def list_buckets(self):
        raise NotImplementedError

    def get_stream(self, bucket, label, as_stream=True):
        raise NotImplementedError

    def put_stream(self, bucket, label, stream_object, params={}):
        raise NotImplementedError

    def del_stream(self, bucket, label):
        raise NotImplementedError

    def get_metadata(self, bucket, label):
        raise NotImplementedError

    def update_metadata(self, bucket, label, params):
        raise NotImplementedError

    def del_metadata_keys(self, bucket, label, keys):
        raise NotImplementedError

