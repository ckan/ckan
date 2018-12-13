#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from ofs.local.zipfile import ZipFile, BadZipfile, LargeZipFile, ZIP_STORED, ZIP_DEFLATED, is_zipfile

from ofs.base import BucketExists, OFSException, OFSInterface, OFSFileNotFound

from pairtree import ppath

import hashlib

from datetime import datetime

from tempfile import mkstemp

from uuid import uuid4

import os

try:
    import json
except ImportError:
    import simplejson as json
    
class NoSuchZipArchive(OFSException):
    pass
class BadZipArchive(OFSException):
    pass

MD_FILE = "ZOFS_persistent_metadata.json"
        
class ZOFS(OFSInterface):
    '''Implementation of an OFS interface to a zip file archive.

    Metadata: This is stored in the metadata/ 'folder' - same filename as the
    original bucket it describes.
    '''
    def __init__(self, zipfile, mode="r", compression=ZIP_STORED, allowZip64=False, hashing_type="md5", quiet=False):
        """Open the ZOFS ZIP file archive with mode read "r", write "w" or append "a"."""
        if mode not in ("r", "w", "a"):
            raise RuntimeError('ZOFS() requires mode "r", "w", or "a" (due to underlying ZipFile class)')
        if mode in ("w", "a") and not quiet:
            print "IMPORTANT: You MUST .close() this ZOFS instance for it to write the ending records in '%s' mode. Otherwise the resultant zip archive will be unreadable." % mode
        self.zipfile = zipfile
        self.mode = mode
        self.compression = compression
        self.allowZip64 = allowZip64
        self.hashing_type = hashing_type
        self.quiet = quiet
        if mode == "r" and not is_zipfile(zipfile):
            raise BadZipArchive, e
        try:
            self.z = ZipFile(self.zipfile, self.mode, self.compression, self.allowZip64)
            #if mode != "r":
            #    """For safety's sake, close the w or a'd archive and open only when in use"""
            #    self.close()
            #    del self.z
        except BadZipfile,e:
            print "Couldn't open the zipfile at '%s'" % zipfile
            print "Got BadZipfile %s error" % e
            raise BadZipArchive, e
        except LargeZipFile,e:
            print "the zipfile requires ZIP64 extensions and those extensions are disabled."
            raise BadZipArchive, e

    def _write(self, z, bucket, label, stream):
        # Not to be used directly
        name = self._zf(bucket, label)
        if self.hashing_type != None:
            hash_gen = getattr(hashlib, self.hashing_type)()
        if hasattr(stream, 'read'):
            size = 0
            fd, filename = mkstemp()
            f = os.fdopen(fd, "wb")
            chunk = stream.read(1024*128)
            while chunk:
                f.write(chunk)
                size = size + len(chunk)
                if self.hashing_type != None:
                    hash_gen.update(chunk)
                chunk = stream.read(1024*128)
            f.close()
            z.write(filename, name)
            os.remove(filename)
        else:
            if self.hashing_type != None:
                hash_gen.update(stream)
            size = len(stream)
            z.writestr(name, stream)
        if self.hashing_type != None:
            return size, '%s:%s' % (self.hashing_type, hash_gen.hexdigest())
        return size, ""
        
    def __del__(self):
        """Unlikely that this will be called, but just in case"""
        self.close()
    
    def close(self):
        # Close the zipfile handle
        self.z.close()
    
    def _zf(self, bucket, label):
        # encodes the ids and turns it into a viable zipfile path
        return "/".join((ppath.id_encode(bucket), label))    # forcing / joining for zipfiles...
    
    def _nf(self, name):
        # decodes the path, and returns a tuple of (bucket, label)
        enc_bucket, label = name.split("/", 1)
        return (ppath.id_decode(enc_bucket), label)
    
    def exists(self, bucket, label):
        '''Whether a given bucket:label object already exists.'''
        fn = self._zf(bucket, label)
        try:
            self.z.getinfo(fn)
            return True
        except KeyError:
            return False

    def claim_bucket(self, bucket=None):
        '''Claim a bucket. -- This is a NOOP as the bucket is a virtual folder 
        in the zipfile and does not exist without files it 'contains'.
        
        Called without a 'bucket' it will respond with a uuid.'''
        if bucket:
            return bucket
        else:
            return uuid4().hex

    def list_labels(self, bucket):
        '''List labels for the given bucket. Due to zipfiles inherent arbitrary ordering,
        this is an expensive operation, as it walks the entire archive searching for individual
        'buckets'

        :param bucket: bucket to list labels for.
        :return: iterator for the labels in the specified bucket.
        '''
        for name in self.z.namelist():
            container, label = self._nf(name.encode("utf-8"))
            if container == bucket and label != MD_FILE:
                yield label
    
    def list_buckets(self):
        '''List all buckets managed by this OFS instance. Like list_labels, this also
        walks the entire archive, yielding the bucketnames. A local set is retained so that
        duplicates aren't returned so this will temporarily pull the entire list into memory
        even though this is a generator and will slow as more buckets are added to the set.
        
        :return: iterator for the buckets.
        '''
        buckets = set()
        for name in self.z.namelist():
            bucket, _ = self._nf(name)
            if bucket not in buckets:
                buckets.add(bucket)
                yield bucket

    def get_stream(self, bucket, label, as_stream=True):
        '''Get a bitstream for the given bucket:label combination.

        :param bucket: the bucket to use.
        :return: bitstream as a file-like object 
        '''
        if self.mode == "w":
            raise OFSException, "Cannot read from archive in 'w' mode"
        elif self.exists(bucket, label):
            fn = self._zf(bucket, label)
            if as_stream:
                return self.z.open(fn)
            else:
                return self.z.read(fn)
        else:
            raise OFSFileNotFound

    def get_url(self, bucket, label):
        '''Get a URL that should point at the bucket:labelled resource. Aimed to aid web apps by allowing them to redirect to an open resource, rather than proxy the bitstream.

        :param bucket: the bucket to use.
        :param label: the label of the resource to get
        :return: a string URI - eg 'zip:file:///home/.../foo.zip!/bucket/label' 
        '''
        if self.exists(bucket, label):
            root = "zip:file//%s" % os.path.abspath(self.zipfile)
            fn = self._zf(bucket, label)
            return "!/".join(root, fn)
        else:
            raise OFSFileNotFound

    def put_stream(self, bucket, label, stream_object, params={}, replace=True, add_md=True):
        '''Put a bitstream (stream_object) for the specified bucket:label identifier.

        :param bucket: as standard
        :param label: as standard
        :param stream_object: file-like object to read from or bytestring.
        :param params: update metadata with these params (see `update_metadata`)
        '''
        if self.mode == "r":
            raise OFSException, "Cannot write into archive in 'r' mode"
        else:
            fn = self._zf(bucket, label)
            params['_creation_date'] = datetime.now().isoformat().split(".")[0]  ## '2010-07-08T19:56:47'
            params['_label'] = label
            if self.exists(bucket, label) and replace==True:
                # Add then Replace? Let's see if that works...
                #z = ZipFile(self.zipfile, self.mode, self.compression, self.allowZip64)
                zinfo = self.z.getinfo(fn)
                size, chksum = self._write(self.z, bucket, label, stream_object)
                self._del_stream(zinfo)
                #z.close()
                params['_content_length'] = size
                if chksum:
                    params['_checksum'] = chksum
            else:
                #z = ZipFile(self.zipfile, self.mode, self.compression, self.allowZip64)
                size, chksum = self._write(self.z, bucket, label, stream_object)
                #z.close()
                params['_content_length'] = size
                if chksum:
                    params['_checksum'] = chksum
            if add_md:
                params = self.update_metadata(bucket, label, params)
            return params
    
    def _del_stream(self, zinfo):
        print "DELETE DISABLED... until I can get it working..."
        pass
        #if self.mode == "a":
        #    self.z.close()
        #    self.z = ZipFile(self.zipfile, "w", self.compression, self.allowZip64)
        #self.z.remove(zinfo)
        #if self.mode == "a":
        #    self.z.close()
        #    self.z = ZipFile(self.zipfile, self.mode, self.compression, self.allowZip64)
        
    
    def del_stream(self, bucket, label):
        '''Delete a bitstream. This needs more testing - file deletion in a zipfile
        is problematic. Alternate method is to create second zipfile without the files
        in question, which is not a nice method for large zip archives.
        '''
        if self.exists(bucket, label):
            name = self._zf(bucket, label)
            #z = ZipFile(self.zipfile, self.mode, self.compression, self.allowZip64)
            self._del_stream(name)
            #z.close()
    
    def _get_bucket_md(self, bucket):
        name = self._zf(bucket, MD_FILE)
        if not self.exists(bucket, MD_FILE):
            raise OFSFileNotFound
        if self.mode !="w":
            #z = ZipFile(self.zipfile, "r", self.compression, self.allowZip64)
            json_doc = self.z.read(name)
            #z.close()
            try:
                jsn = json.loads(json_doc)
                return jsn
            except ValueError:
                raise OFSException, "Cannot read metadata for %s" % bucket
        else:
            raise OFSException, "Cannot read from archive in 'w' mode"

    def get_metadata(self, bucket, label):
        '''Get the metadata for this bucket:label identifier.
        '''
        if self.mode !="w":
            try:
                jsn = self._get_bucket_md(bucket)
            except OFSFileNotFound:
                # No MD found...
                return {}
            except OFSException, e:
                raise OFSException, e
            if jsn.has_key(label):
                return jsn[label]
            else:
                return {}
        else:
            raise OFSException, "Cannot read md from archive in 'w' mode"

    def update_metadata(self, bucket, label, params):
        '''Update the metadata with the provided dictionary of params.

        :param parmams: dictionary of key values (json serializable).
        '''
        if self.mode !="r":
            try:
                payload = self._get_bucket_md(bucket)
            except OFSFileNotFound:
                # No MD found... create it
                payload = {}
                for l in self.list_labels(bucket):
                    payload[l] = {}
                    payload[l]['_label'] = l
                if not self.quiet:
                    print "Had to create md file for %s" % bucket
            except OFSException, e:
                raise OFSException, e
            if not payload.has_key(label):
                payload[label] = {}
            payload[label].update(params)
            self.put_stream(bucket, MD_FILE, json.dumps(payload), params={}, replace=True, add_md=False)
            return payload[label]
        else:
            raise OFSException, "Cannot update MD in archive in 'r' mode"
            
    def del_metadata_keys(self, bucket, label, keys):
        '''Delete the metadata corresponding to the specified keys.
        '''
        if self.mode !="r":
            try:
                payload = self._get_bucket_md(bucket)
            except OFSFileNotFound:
                # No MD found... 
                raise OFSFileNotFound, "Couldn't find a md file for %s bucket" % bucket
            except OFSException, e:
                raise OFSException, e
            if payload.has_key(label):
                for key in [x for x in keys if payload[label].has_key(x)]:
                    del payload[label][key]
            self.put_stream(bucket, MD_FILE, json.dumps(payload), params={}, replace=True, add_md=False)
        else:
            raise OFSException, "Cannot update MD in archive in 'r' mode"

