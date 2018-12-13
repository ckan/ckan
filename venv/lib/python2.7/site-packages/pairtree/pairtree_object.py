#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Conventions used:

From http://www.cdlib.org/inside/diglib/pairtree/pairtreespec.html version 0.1

This is a convenience object, used as a proxy for an object inside a pairtree store.
As such, it shouldn't be instanciated directly.
"""

import os, sys, shutil

import codecs

import string

from storage_exceptions import *

class PairtreeStorageObject(object):
    """
    The important methods:

        -  add_bytestream(filename, bytestream, path=None, buffer_size=None):
        -. get_bytestream(filename, streamable=False, path=None):
        -  del_file(filename, path=None):
        -  list_parts(path=None):

    First, setup up a simple store in 'data' and get an object called 'bar'
    (which will be equivalent to 'http://example.org/bar')
    
    >>> from pairtree import PairtreeStorageFactory
    >>> factory = PairtreeStorageFactory()
    >>> store = factory.get_store(store_dir='data', uri_base='http://example.org/')
    >>> bar = store.get_object('bar')

    Now add a simple string to a file called 'foo.txt'

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

        -  L{add_bytestream_by_path}(self, filepath, bytestream, buffer_size=None):
        -  L{del_file_by_path}(self, filepath, bytestream):
        -  L{get_bytestream_by_path}(self, filepath, streamable=False):

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
    def __init__(self, id, fs_store_client):
        """
        @param id: Identifier for pairtree object
        @type id: identifier
        @param fs_store_client: A reference to an instance of L{PairtreeStorageClient}
        @type fs_store_client: L{PairtreeStorageClient}
        """
        self.fs = fs_store_client
        if id.startswith(self.fs.uri_base):
            self.id = id[len(self.fs.uri_base):]
        else:
            self.id = id
        self.uri = "%s%s" % (self.fs.uri_base, id)

    def add_bytestream(self, filename, bytestream, path=None, buffer_size=None):
        """
        Add a string or file to a given filename within this object. a C{path} may
        be supplied to store the file within a subdirectory of the object.
        
        @param path: (Optional) subdirectory path to store file in
        @type path: Directory path
        @param filename: Name of the file to write to
        @type filename: filename
        @param bytestream: Either a string or a file-like object to read from
        @type bytestream: L{str}|L{file}
        @param buffer_size: (Optional) Used for streaming filelike objects - defines the size of the buffer
        to read in each cycle.
        @type buffer_size: L{int}
        """
        if buffer_size:
            return self.fs.put_stream(self.id, path, filename, bytestream, buffer_size)
        return self.fs.put_stream(self.id, path, filename, bytestream)

    def add_bytestream_by_path(self, filepath, bytestream, buffer_size=None):
        """
        Add a string or file to a given filename within this object.
        
        The following adds the contents of footxt into a file 'foo.txt' in a
        subdirectory of the object 'data', which may or may not have existed prior
        to this call:
        
        >>> object.add_bytestream_by_path('data/foo.txt', footxt)
        
        @param filepath: (Optional) path to store the file in
        @type filepath: path to a file
        @param bytestream: Either a string or a file-like object to read from
        @type bytestream: L{str}|L{file}
        @param buffer_size: (Optional) Used for streaming filelike objects - defines the size of the buffer
        to read in each cycle.
        @type buffer_size: L{int}
        """
        path, filename = os.path.split(filepath)
        if buffer_size:
            return self.add_bytestream(filename, bytestream, path, buffer_size)
        return self.add_bytestream(filename, bytestream, path)

    def get_bytestream(self, filename, streamable=False, path=None, appendable=False):
        """
        Reads a file from a pairtree object - If streamable is set to True,
        this returns the filehandle for that file, which must be C{close()}'d
        once finished with. In python 2.6 and above, this can be done easily:
        
        >>> with object.get_bytestream('image001.tif', True, 'data/images') as stream:
                # Do something with the C{stream} handle
                pass
        
        stream is closed at the end of a C{with} block
        
        If appendable is set to True, then the file is opened "wb+" and can accept writes.
        Otherwise, the file is opened read-only.
        
        @param path: (Optional) subdirectory path to retrieve file from
        @type path: Directory path
        @param filename: Name of the file to read in
        @type filename: filename
        @param streamable: If True, returns a filelike handle to C{read()} from - 
        I{remember to C{close()} the file!} If False, reads in the file into a 
        bytestring and return that instead.
        @type streamable: True|False
        @returns: Either L{file} or L{str}
        """
        if appendable:
            return self.fs.get_appendable_stream(self.id, path=path, stream_name=filename)
        else:
            return self.fs.get_stream(self.id, path=path, stream_name=filename, streamable=streamable)

    def get_bytestream_by_path(self, filepath, streamable=False, appendable=False):
        """
        As L{get_bytestream}, but can ask for a file via a path:
        
        >>> print object.get_bytestream('data/foo/mytext.txt')
        ............
        
        @param filepath: (Optional) path of the file inside the object
        @type filepath: path to a file
        @param streamable: If True, returns a filelike handle to C{read()} from - 
        I{remember to C{close()} the file!} If False, reads in the file into a 
        bytestring and return that instead.
        @type streamable: True|False
        @returns: Either L{file} or L{str}
        """
        path, filename = os.path.split(filepath)
        return self.get_bytestream(filename, streamable, path, appendable)

    def add_file(self, from_file_location, path=None, new_filename=None, buffer_size=None):
        """
        Adds a file from a given location. Currently, the copy is due via python buffering
        the read from one file to the other. Might be easily replaceable with a C{shutil.copy}
        at a later date.
        
        If no new filename is set, it will use the original filename
        
        Aside from this, it works in the same fasion as L{add_bytestream}
        
        @param from_file_location: File path to read the file from
        @type from_file_location: Directory path
        @param path: (Optional) subdirectory within object to store file in
        @type path: Directory path
        @param new_filename: Name of the file to write to
        @type new_filename: filename
        @param buffer_size: (Optional) Used for streaming filelike objects - defines the size of the buffer
        to read in each cycle.
        @type buffer_size: L{int}
        """
        if os.path.exists(from_file_location):
            if not new_filename:
                _, new_filename = os.path.split(from_file_location)
            fh = open(from_file_location, 'rb')
            if buffer_size:
                return self.fs.put_stream(self.id, path, new_filename, bytestream=fh, buffer_size=buffer_size)
            return self.fs.put_stream(self.id, path, new_filename, bytestream=fh)
            fh.close()
        else:
            raise FileNotFoundException

    def del_file(self, filename, path=None):
        """
        Delete a file from the object. 
        
        If path is set, it will attempt to delete from that subpath.
        
        @param filename: Name of the file to delete
        @type filename: filename
        @param path: (Optional) subdirectory within object to delete file from
        @type path: Directory path
        """
        return self.fs.del_stream(self.id, filename, path)

    def del_file_by_path(self, filepath):
        """
        Delete a file from the object using the filepath as a subpath within the object.
        
        Eg::
        
            object_root --  foo.txt
                            foo2.txt
                            data    --  image1.jpg
                                        image2.jpg
        
        >>> object.del_file_by_path('data/image2.jpg')
        >>>
        
        @param filepath: subdirectory filepath within object to delete
        @type filepath: Directory path
        """
        path, filename = os.path.split(filepath)
        return self.del_file(filename, path)

    def del_path(self, subpath, recursive=False):
        """
        Delete a subpath from the object, and can do so recursively (optional)
        If the path is found to be not "empty" (ie has not parts in it) and
        recursive is not True, then it will raise a L{PathIsNotEmptyException}
        @param path: subdirectory path to delete
        @type path: Directory path
        @param recursive: Whether the delete is recursive (think rm -rf)
        @type recursive: bool
        """
        return self.fs.del_path(self.id, subpath, recursive)

    def list_parts(self, path=None):
        """
        List all the parts of object's root.
        
        If path is supplied, the parts in that subdirectory are returned.
        
        If the subpath doesn't exist, a L{ObjectNotFoundException} will be raised.
        
        >>> object.list_parts('data/images')
        [ 'image001.tif', 'image....    ]
        
        @param path: (Optional) List the parts contained in C{path}'s subdirectory
        @type path: Directory path
        @returns: L{list}
        """
        return self.fs.list_parts(self.id, path)

    def isfile(self, filepath):
        """
        Returns True or False depending on whether the path is a file or not.
        
        If the file doesn't exist, False is returned.
        
        @param path: Path to be tested
        @type path: Directory path
        @returns: L{bool}
        """
        return self.fs.isfile(self.id, filepath)
        
    def isdir(self, filepath):
        """
        Returns True or False depending on whether the path is a subdirectory or not.
        
        If the path doesn't exist, False is returned.
        
        @param path: Path to be tested
        @type path: Directory path
        @returns: L{bool}
        """
        return self.fs.isdir(self.id, filepath)

    def stat(self, filepath):
        """
        Returns the os.stat for a given file, or False if the file doesn't exist
        
        @param id: id of the object
        @type id: string
        @param filepath: Path to be tested
        @type filepath: Directory path
        @returns L{posix.stat_result} or False
        """
        if self.isfile(filepath):
            return self.fs.stat(self.id, filepath)
        else:
            return False

    def id_to_dirpath(self):
        """
        Get the path to the top of this object

            -  I{"foobar://ark.1" --> "fo/ob/ar/+=/ar/k,/1"}

        @returns: A directory path to the object's root directory
        """
#        return os.sep.join(self._id_to_dir_list(id))
        return self.fs._id_to_dirpath(self.id)
