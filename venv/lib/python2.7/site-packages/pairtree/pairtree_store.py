#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
FS Pairtree storage - Factory
=============================

Conventions used:

From http://www.cdlib.org/inside/diglib/pairtree/pairtreespec.html version 0.1

This is a simple Factory-style class, which can produce pairtree store clients.

Usage
=====

>>> from pairtree import PairtreeStorageFactory
>>> factory = PairtreeStorageFactory()

To create a pairtree store in I{mystore/} to hold objects which have a URI base of
I{http://example.org/ark:/123}

>>> store = factory.get_store(store_dir='mystore', uri_base='http://example.org/ark:/123')

"""

from pairtree_client import PairtreeStorageClient

class PairtreeStorageFactory(object):

    def get_store(self, store_dir="data", uri_base=None, shorty_length=2, hashing_type = None):
        """
        Get a store - if the store does not exist, one will be instanciated
        
        If hashing_type is set to one of the hashing algorithms supported by
        hashlib - ['md5', 'sha1', 'sha224','sha256','sha384','sha512'] then
        all bytestreams will be checksummed when added or updated and their sums returned.
        
        @param store_dir: The file directory where the pairtree store is
        @type store_dir: A path to a directory, relative or absolute
        @param uri_base: The URI base for the store
        @type uri_base: A URI fragment, like "http://example.org/"
        @param shorty_length: The size of the shorties in the pairtree implementation (Default: 2)
        @type shorty_length: integer
        @param hashing_type: The name of the algorithm to use when hashing files, if left as None, this is disabled.
        @type hashing_type: Any supported by C{hashlib}
        @returns: L{PairtreeStorageClient}
        """
        if hashing_type and hashing_type not in ['md5', 'sha1', 'sha224','sha256','sha384','sha512']:
            raise Exception("hashing type must be on of the supported hashlib types: md5, sha1, sha224, sha256, sha384, sha512")
        return PairtreeStorageClient(uri_base, store_dir, shorty_length, hashing_type)
