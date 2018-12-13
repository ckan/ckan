#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import with_statement

from storedjson import PersistentState

from pairtreestore import PTOFS

from ofs.base import OFSInterface, OFSFileNotFound, BucketExists, OFSException

from datetime import datetime

from uuid import uuid4

class MDOFS(OFSInterface):
    '''Implementation of a local OFS style store, which has a focus to hold
    small numbers of files for very large numbers of objects. Created
    as a response to a need to store records for 3+ million objects, without 
    hitting hard filesystem limits.
    
    Uses pairtree storage, but a pairtree id only comprises part of a bucket id.

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
    def __init__(self, storage_dir="metadata", uri_base="urn:uuid:", hashing_type="md5", shorty_length=2, tail_retention=3, _fsep="-,-"):
        self.storage_dir = storage_dir
        self.uri_base = uri_base
        self.hashing_type = hashing_type
        self.shorty_length = shorty_length
        self.tail=tail_retention
        self.fsep = _fsep
        self._open_store()
    
    def _open_store(self):
        self._ptstore = PTOFS(self.storage_dir, self.uri_base, self.hashing_type, self.shorty_length)
    
    def _toptid(self, bucket):
        ptid = bucket[:-self.tail]
        frag = bucket[len(bucket)-self.tail:]
        return ptid, frag
    
    def _topt(self, bucket, label):
        ptid = bucket[:-self.tail]
        fn = bucket[len(bucket)-self.tail:]+self.fsep+label
        return (ptid, fn)
    
    def _frompt(self, ptid, fn):
        frag, label = fn.rsplit(self.fsep,1)
        return (ptid+frag, label)
    
    def exists(self, bucket, label=None):
        if label:
            ptid, fn = self._toptid(bucket, label)
            return self._ptstore.exists(ptid, fn)
        else:
            ptid, prefix = self._toptid(bucket)
            return self._ptstore.exists(ptid)
            #  Following works only if a file has been stored
            #  in  a given bucket
            #
            #labels = self._ptstore.list_labels(ptid)
            #if labels:
            #    for item in labels:
            #        if item.startswith(prefix):
            #            return True
            #return False

    def claim_bucket(self, bucket=None):
        if not bucket:
            bucket = uuid4().hex
            while(self.exists(bucket)):
                bucket = uuid4().hex
        ptid, _ = self._toptid(bucket)
        r_id = self._ptstore.claim_bucket(ptid)
        return bucket
        

    def list_labels(self, bucket):
        ptid, prefix = self._toptid(bucket)
        for item in self._ptstore.list_labels(ptid):
            if item.startswith(prefix):
                _, label = self._frompt(ptid, item)
                yield label
    
    def list_buckets(self):
        b_set = set()
        for ptid in self._ptstore.list_buckets():
            for item in self._ptstore.list_labels(ptid):
                bucket, label = self._frompt(ptid, item)
                if bucket not in b_set:
                    b_set.add(bucket)
                    yield bucket
        
    def get_stream(self, bucket, label, as_stream=True):
        ptid, fn = self._topt(bucket, label)
        return self._ptstore.get_stream(ptid, fn, as_stream)

    def get_url(self, bucket, label):
        ptid, fn = self._topt(bucket, label)
        return self._ptstore.get_url(ptid, fn)

    def put_stream(self, bucket, label, stream_object, params={}):
        ptid, fn = self._topt(bucket, label)
        params['_label'] = label
        return self._ptstore.put_stream(ptid, fn, stream_object, params)

    def del_stream(self, bucket, label):
        ptid, fn = self._topt(bucket, label)
        return self._ptstore.del_stream(ptid, fn)
        
    def get_metadata(self, bucket, label):
        ptid, fn = self._topt(bucket, label)
        return self._ptstore.get_metadata(ptid, fn)

    def update_metadata(self, bucket, label, params):
        ptid, fn = self._topt(bucket, label)
        return self._ptstore.update_metadata(ptid, fn, params)

    def del_metadata_keys(self, bucket, label, keys):
        ptid, fn = self._topt(bucket, label)
        return self._ptstore.del_metadata_keys(ptid, fn, keys)

