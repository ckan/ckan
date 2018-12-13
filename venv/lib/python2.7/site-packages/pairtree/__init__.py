#!/usr/bin/python
# -*- coding: utf-8 -*-


"""
FS Pairtree storage
===================

Conventions used:

From http://www.cdlib.org/inside/diglib/pairtree/pairtreespec.html version 0.1

NOTICE
======

The Pairtree specification on which this implementation is based is (c) 2009 UC Regents.

Various regexes used in path to id conversion and the bulk of the unittests were 
contributed by Erik Hetzner, based on John Kunze's work, also (c) 2009 UC Regents
and released under the Apache license.

The ppath script
================

A ppath script is included for convenience to be used in shell scripts or similar. Eg:

C{ppath topath} examples::

    $ vim mystore/pairtree_root/`ppath topath document:105/data/doc.txt`
    (Opens the file at mystore/pairtree_root/do/cu/me/nt/+1/05/data/doc.txt)
    $ cp `ppath topath foo:bar/1.txt` `ppath topath bar:foo/2.txt`

C{ppath toid} examples::

    data/subjects/pairtree_root/HA/SS/ET/ROOT$ ppath toid `pwd`
    HASSET/ROOT
    
Quick Start:
============

>>> from pairtree import *

>>> # Get the store 'factory'
>>> f = PairtreeStorageFactory()

The factory object is solely there to create clients for individual pairtree
stores. For example:

>>> store_foo = f.get_store(store_dir="data", uri_base="http://")

This will create the following on disc in a directory called 'data' if it doesn't already exist::

    $ ls -R data/
    data/:
    pairtree_prefix  pairtree_root  pairtree_version0_1

    data/pairtree_root:

Where 
    1. the file 'pairtree_prefix' contains just "http://"
    2. the file 'pairtree_version0_1' contains::
    
       This directory conforms to Pairtree Version 0.1.
       Updated spec: http://www.cdlib.org/inside/diglib/pairtree/pairtreespec.html

Note, if data *had* already existed and was a pairtree store, the uri_base would
have been read from the prefix file and override the one supplied above.

Also, if you try to create a store over a directory that already exists, but which isn't
a pairtree store that it can recognise, it will raise a NotAPairtreeStoreException.

Valid store names fit the regex ^[A-z][A-z0-9]* - but this is an arbitrary limitation
and can be removed if it is seen as unnecessary.

Creating and Getting store object:
==================================

Two main commands for this activity, eg continuing on:

>>> bar = store_foo.create_object('bar')
>>>

Note that reissuing that command again will raise an Exception:

>>> bar = store_foo.create_object('bar')
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
  File "build/bdist.linux-i686/egg/pairtree/pairtree_client.py", line 235, in create_object
pairtree.storage_exceptions.ObjectAlreadyExistsException

There is also a 'get_object' command, which is more accommodating, as it can be passed
a fairly self-explanatory flag, which by default will create the object if it doesn't exist:

I{get_object(self, id=None, create_if_doesnt_exist=True)}

>>> bar = store_foo.get_object('bar')

Setting this flag to False, will cause it to raise an exception if it cannot find an object.

>>> fake = store_foo.get_object('doesnotexist', create_if_doesnt_exist=False)
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
  File "build/bdist.linux-i686/egg/pairtree/pairtree_client.py", line 231, in get_object
pairtree.storage_exceptions.ObjectNotFoundException

(note that fake = store_foo.get_object('doesnotexist', False) is equivalent to the above line)

A pairtree object:
==================

The important methods:

    -  add_bytestream(filename, bytestream, path=None, buffer_size=None):
    -. get_bytestream(filename, streamable=False, path=None):
    -  del_file(filename, path=None):
    -  list_parts(path=None):

E.g. - Examples speak louder than words

>>> bar.add_bytestream('foo.txt', 'can be any sequence of bytes')
>>> bar.list_parts()
['foo.txt']
>>> 

Adding buffered content from a file:

>>> with open('/home/ben/Firefox_wallpaper.png','rb') as stream:
...   bar.add_bytestream('Firefox_wallpaper.png', stream)
... 
>>> 

Adding the same file to magic/path/inside/object - paths are automatically created on
demand.

>>> with open('/home/ben/Firefox_wallpaper.png','rb') as stream:
...   bar.add_bytestream('Firefox_wallpaper.png', stream, path='magic/path/inside/object')
... 
>>> 

Removing the first copy of that file, which was added to the wrong place:

>>> bar.del_file('Firefox_wallpaper.png')
>>> bar.list_parts()
['magic', 'foo.txt']
>>> bar.list_parts('magic/path')
['inside']
>>> bar.list_parts('magic/path/inside/object')
['Firefox_wallpaper.png']
>>> 

There are also some convenience methods:

    -  add_bytestream_by_path(self, filepath, bytestream, buffer_size=None):
    -  del_file_by_path(self, filepath, bytestream):
    -  get_bytestream_by_path(self, filepath, streamable=False):

The I{by_path} suffix means that you can give it the whole path as one, and it will
try to figure out what is intended, for example, consider the png we placed in a nested
directory earlier:

>>> with open('/home/ben/Firefox_wallpaper.png','rb') as stream:
...   bar.add_bytestream('Firefox_wallpaper.png', stream, path='magic/path/inside/object')
... 

This can be written as:

>>> with open('/home/ben/Firefox_wallpaper.png','rb') as stream:
...   bar.add_bytestream_by_path('magic/path/inside/object/Firefox_wallpaper.png', stream)
... 

Getting files from an object
============================

The flag I{streamable} is key here - if this is set to True, then you will be passed
a file handle, which you must remember to close or use the construct:

>>> with bar.get_bytestream('foo.txt', streamable=True) as text:
...   print text.read()
... 
>>>

This is very useful for large files you wish to scan through, but do not need to hold
in memory all at the same time.

By setting streamable to False, the entire file is read into memory and returned:

>>> print bar.get_bytestream('foo.txt')
can be any sequence of bytes
"""

__version__ = '0.5.2'

from pairtree_client import *
from pairtree_store import *
from pairtree_object import *
from pairtree_revlookup import PairtreeReverseLookup
import pairtree_path as ppath
from pairtree_path import id_encode, id_decode
from storage_exceptions import *

def id2path(id):
    """
    pass in a pairtree id and get back a path
    """
    path = ppath.id_to_dirpath(id)
    return path

def path2id(path):
    """
    pass in a pairtree path and get back an id
    """
    return ppath.get_id_from_dirpath(path)

