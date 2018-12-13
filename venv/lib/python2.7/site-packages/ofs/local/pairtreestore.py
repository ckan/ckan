#!/usr/bin/env python

from __future__ import with_statement

from storedjson import PersistentState

from pairtree import PairtreeStorageClient
from pairtree import id_encode, id_decode
from pairtree import FileNotFoundException, ObjectNotFoundException

from ofs.base import OFSInterface, OFSException, BucketExists

from datetime import datetime

from uuid import uuid4

class OFSNotFound(Exception):
    pass

class PTOFS(OFSInterface):
    '''OFS backend backed onto the filesystem and using PairTree_.

    .. _PairTree: http://pypi.python.org/pypi/Pairtree
    '''
    def __init__(self, storage_dir="data", uri_base="urn:uuid:", hashing_type="md5", shorty_length=2):
        self.storage_dir = storage_dir
        self.uri_base = uri_base
        self.hashing_type = hashing_type
        self.shorty_length = shorty_length
        self._open_store()
    
    def _open_store(self):
        if self.hashing_type:
            self._store = PairtreeStorageClient(self.uri_base, self.storage_dir, shorty_length=self.shorty_length, hashing_type=self.hashing_type)
        else:
            self._store = PairtreeStorageClient(self.uri_base, self.storage_dir, shorty_length=shorty_length)

    def exists(self, bucket, label=None):
        if self._store.exists(bucket):
            if label:
                return self._store.isfile(bucket, label)
            else:
                return True
    
    def _get_object(self, bucket):
        po = self._store.get_object(bucket)
        json_payload = PersistentState(po.id_to_dirpath())
        return (po, json_payload)

    def _setup_item(self, bucket):
        _, json_payload = self._get_object(bucket)
        json_payload.sync()
    
    def claim_bucket(self, bucket=None):
        if bucket:
            if self.exists(bucket):
                raise BucketExists
        else:
            bucket = uuid4().hex
            while(self.exists(bucket)):
                bucket = uuid4().hex
        self._setup_item(bucket)
        return bucket
        
    def list_labels(self, bucket):
        if self.exists(bucket):
            _, json_payload = self._get_object(bucket)
            return json_payload.keys()

    def list_buckets(self):
        return self._store.list_ids()
        
    def put_stream(self, bucket, label, stream_object, params={}):
        ## QUESTION: do we enforce that the bucket's have to be 'claimed' first?
        ## NB this method doesn't care if it has been
        po, json_payload = self._get_object(bucket)

        if label in json_payload.keys():
            creation_date = None
        else:
            # New upload - record creation date
            creation_date = datetime.now().isoformat().split(".")[0]  ## '2010-07-08T19:56:47'
            if params.has_key('_label'):
                json_payload[label] = {"_label":params['_label']}
            else:
                json_payload[label] = {"_label":label}

        hash_vals = po.add_bytestream_by_path(label, stream_object)
        stat_vals = po.stat(label)
        
        # Userland parameters for the file
        cleaned_params = dict( [ (k, params[k]) for k in params if not k.startswith("_")])
        json_payload[label].update(cleaned_params)
        try:
            json_payload[label]['_content_length'] = int(stat_vals.st_size)
        except TypeError:
            print "Error getting filesize from os.stat().st_size into an integer..."
        if creation_date:
            json_payload[label]['_creation_date'] = creation_date
            json_payload[label]['_last_modified'] = creation_date
        else:
            # Modification date
           json_payload[label]['_last_modified'] = datetime.now().isoformat().split(".")[0]
        # Hash details:
        if hash_vals:
            json_payload[label]['_checksum'] = "%s:%s" % (hash_vals['type'], hash_vals['checksum'])
        json_payload.sync()
        return json_payload.state[label]

    def get_stream(self, bucket, label, as_stream=True):
        if self.exists(bucket):
            po, json_payload = self._get_object(bucket)
            if self.exists(bucket, label):
                return po.get_bytestream(label, streamable=as_stream, path=None, appendable=False)
        raise FileNotFoundException

    def get_url(self, bucket, label):
        if self.exists(bucket) and self.exists(bucket, label):
            return self._store.get_url(bucket, label)
        else:
            raise FileNotFoundException
    
    def get_metadata(self, bucket, label):
        if self.exists(bucket):
            _, json_payload = self._get_object(bucket)
            if json_payload.has_key(label):
                return json_payload.state[label]
        raise FileNotFoundException
    
    def update_metadata(self, bucket, label, params):
        if self.exists(bucket, label) and isinstance(params, dict):
            _, json_payload = self._get_object(bucket)
            # Userland parameters for the file
            cleaned_params = dict([(k, params[k]) for k in params if not k.startswith("_")])
            json_payload[label].update(cleaned_params)
            json_payload.sync()
            return json_payload.state[label]
        else:
            raise FileNotFoundException
    
    def del_metadata_keys(self, bucket, label, keys):
        if self.exists(bucket, label) and isinstance(keys, list):
            _, json_payload = self._get_object(bucket)
            for key in [x for x in keys if not x.startswith("_")]:
                if key in json_payload[label].keys():
                    del json_payload[label][key]
            json_payload.sync()
            return json_payload.state[label]
        else:
            raise FileNotFoundException

    def del_stream(self, bucket, label):
        if self.exists(bucket, label):
            # deletes the whole object for uuid
            self._store.del_stream(bucket, label)
            _, json_payload = self._get_object(bucket)
            if json_payload.has_key(label):
                del json_payload[label]
            json_payload.sync()
        else:
            raise FileNotFoundException
