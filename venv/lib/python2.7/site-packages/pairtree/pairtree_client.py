#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Conventions used:

From http://www.cdlib.org/inside/diglib/pairtree/pairtreespec.html version 0.1

This client handles all of the pairtree conventions, and provides a Pairtree object
to make it easier to interact with.

Usage
=====

>>> from pairtree import PairtreeStorageClient

To create a pairtree store in I{mystore/} to hold objects which have a URI base of
I{http://example.org/ark:/123}

>>> store = PairtreeStorageClient(store_dir='mystore', uri_base='http://example.org/ark:/123')

"""

import os, sys, shutil

import codecs

import string

import re

from storage_exceptions import *

from pairtree_object import PairtreeStorageObject

import pairtree_path as ppath

import hashlib

class PairtreeStorageClient(object):
    """A client that oversees the implementation of the Pairtree FS specification
    version 0.1.

    >>> from pairtree import PairtreeStorageClient
    >>> store = PairtreeStorageClient(store_dir='data', uri_base="http://")

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
    a pairtree store that it can recognise, it will raise a L{NotAPairtreeStoreException}.
    """
    def __init__(self, uri_base, store_dir, shorty_length=2, hashing_type=None):
        """
        Constructor
        @param store_dir: The file directory where the pairtree store is
        @type store_dir: A path to a directory, relative or absolute
        @param uri_base: The URI base for the store
        @type uri_base: A URI fragment, like "http://example.org/"
        @param shorty_length: The size of the shorties in the pairtree implementation (Default: 2)
        @type shorty_length: integer
        @param hashing_type: The name of the algorithm to use when hashing files, if left as None, this is disabled.
        @type hashing_type: Any supported by C{hashlib}
        """
        self.store_dir = store_dir
        self.pairtree_root = os.path.join(self.store_dir, 'pairtree_root')
        self.uri_base = None
        if uri_base:
            self.uri_base = uri_base
        self.shorty_length = shorty_length
        self.hashing_type = hashing_type
        # regexes
        self._encode = re.compile(r"[\"*+,<=>?\\^|]|[^\x21-\x7e]", re.U)
        self._decode = re.compile(r"\^(..)", re.U)
        
        self._init_store()

    def __char2hex(self, m):
        return ppath.char2hex(m)

    def __hex2char(self, m):
        return ppath.hex2char(m)

    def _rm_uribase(self, id):
        if id.startswith(self.uri_base):
            return id[len(self.uri_base):]
        return id

    def id_encode(self, id):
        """
        The identifier string is cleaned of characters that are expected to occur rarely
        in object identifiers but that would cause certain known problems for file systems.
        In this step, every UTF-8 octet outside the range of visible ASCII (94 characters
        with hexadecimal codes 21-7e) [ASCII] (Cerf, “ASCII format for network interchange,”
        October 1969.), as well as the following visible ASCII characters::

           "   hex 22           <   hex 3c           ?   hex 3f
           *   hex 2a           =   hex 3d           ^   hex 5e
           +   hex 2b           >   hex 3e           |   hex 7c
           ,   hex 2c

        must be converted to their corresponding 3-character hexadecimal encoding, ^hh,
        where ^ is a circumflex and hh is two hex digits. For example, ' ' (space) is
        converted to ^20 and '*' to ^2a.

        In the second step, the following single-character to single-character conversions
        must be done::

               / -> =
               : -> +
               . -> ,

        These are characters that occur quite commonly in opaque identifiers but present
        special problems for filesystems. This step avoids requiring them to be hex encoded
        (hence expanded to three characters), which keeps the typical ppath reasonably
        short. Here are examples of identifier strings after cleaning and after
        ppath mapping::

            id:  ark:/13030/xt12t3
                ->  ark+=13030=xt12t3
                ->  ar/k+/=1/30/30/=x/t1/2t/3/
            id:  http://n2t.info/urn:nbn:se:kb:repos-1
                ->  http+==n2t,info=urn+nbn+se+kb+repos-1
                ->  ht/tp/+=/=n/2t/,i/nf/o=/ur/n+/n/bn/+s/e+/kb/+/re/p/os/-1/
            id:  what-the-*@?#!^!?
                ->  what-the-^2a@^3f#!^5e!^3f
                ->  wh/at/-t/he/-^/2a/@^/3f/#!/^5/e!/^3/f/

        (From section 3 of the Pairtree specification)

        @param id: Encode the given identifier according to the pairtree 0.1 specification
        @type id: identifier
        @returns: A string of the encoded identifier
        """
        return ppath.id_encode(id)

    def id_decode(self, id):
        """
        This decodes a given identifier from its pairtree filesystem encoding, into
        its original form:
        @param id: Identifier to decode
        @type id: identifier
        @returns: A string of the decoded identifier
        """
        return ppath.id_decode(id)

    def _get_id_from_dirpath(self, dirpath):
        """
        Internal - method for discovering the pairtree identifier for a
        given directory path.

        E.g.  pairtree_root/fo/ob/ar/+/  --> 'foobar:'

        @param dirpath: Directory path to decode
        @type dirpath: Path to object's root
        @returns: Decoded identifier
        """
        #path = self._get_path_from_dirpath(dirpath)
        #return self.id_decode("".join(path))
        return ppath.get_id_from_dirpath(dirpath, self.pairtree_root)

    def _get_path_from_dirpath(self, dirpath):
        """
        Internal - walks a directory chain and builds a list of the directory shorties
        relative to the pairtree_root

        @param dirpath: Directory path to walk
        @type dirpath: Directory path
        """
#        head, tail = os.path.split(dirpath)
#        path = [tail]
#        while not self.pairtree_root == head:
#            head, tail = os.path.split(head)
#            path.append(tail)
#        path.reverse()
#        return path
        return ppath.get_path_from_dirpath(dirpath, self.pairtree_root)


    def _id_to_dirpath(self, id):
        """
        Internal - method for turning an identifier into a pairtree directory tree
        of shorties.

            -  I{"foobar://ark.1" --> "fo/ob/ar/+=/ar/k,/1"}

        @param id: Identifer for a pairtree object
        @type id: identifier
        @returns: A directory path to the object's root directory
        """
        
#        return os.sep.join(self._id_to_dir_list(id))
        return ppath.id_to_dirpath(self._rm_uribase(id), self.pairtree_root, self.shorty_length)

    def _id_to_dir_list(self, id):
        """
        Internal - method for turning an identifier into a list of pairtree 
        directory tree of shorties.

            -  I{"foobar://ark.1" --> ["fo","ob","ar","+=","ar","k,","1"]}

        @param id: Identifer for a pairtree object
        @type id: identifier
        @returns: A list of directory path fragments to the object's root directory
        """
#        enc_id = self.id_encode(id)
#        dirpath = [self.pairtree_root]
#        while enc_id:
#            dirpath.append(enc_id[:self.shorty_length])
#            enc_id = enc_id[self.shorty_length:]
#        return dirpath
        return ppath.id_to_dir_list(self._rm_uribase(id), self.pairtree_root, self.shorty_length)
        
    def _init_store(self):
        """
        Initialise the store if the directory doesn't exist. Create the basic structure
        needed and write the prefix to disc.

        If the store directory exists, one of two things can happen:
            1. If that directory can be understood by this library as a pairtree store,
               it will attempt to read in the correct pairtree_prefix to use, instead of
               the supplied uri_base.
            2. If the directory cannot be understood, a L{NotAPairtreeStoreException} will
               be raised.
        """
        if not os.path.exists(self.store_dir):
            if self.uri_base:
                os.mkdir(self.store_dir)
                f = open(os.path.join(self.store_dir, "pairtree_version0_1"), "w")
                f.write("This directory conforms to Pairtree Version 0.1. Updated spec: http://www.cdlib.org/inside/diglib/pairtree/pairtreespec.html")
                f.close()
                f = open(os.path.join(self.store_dir, "pairtree_prefix"),"w")
                f.write(self.uri_base)
                f.close()
                os.mkdir(self.pairtree_root)
            else:
                raise NotAPairtreeStoreException("""No uri_base set for a non-existent
                                                    store - store cannot be instanciated""")
        else:
            if os.path.exists(os.path.join(self.store_dir, "pairtree_version0_1")):
                """Seems to be a pairtree0_1 compliant 'store'"""
                if os.path.exists(os.path.join(self.store_dir, "pairtree_prefix")):
                    """Read the uri base of this store"""
                    f = open(os.path.join(self.store_dir, "pairtree_prefix"),"r")
                    prefix = f.read().strip()
                    f.close()
                    self.uri_base = prefix
            else:
                raise NotAPairtreeStoreException

        if not os.path.isdir(self.store_dir):
            raise NotAPairtreeStoreException

    def list_ids(self):
        """
        Walk the store, and build a list of pairtree conformational objects in the
        store. This will return objects in 'split-ends' and will function correctly
        as long as non-shortie directorys are just that; non-shortie directories must
        have longer labels than the shorties - e.g::

              ab -- cd -- ef -- obj -- foo.txt
                     |     |
                     |     ---- gh
                     |           |
                     |           -- obj -- foo.txt
                     |
                     ---- e -- obj -- foo.txt

              This method will return ['abcdef', 'abcde', 'abcdefgh'] as ids in this
              store.
        
        Returns a generator, not a plain list since version 0.4.12

        @returns: L{generator}
        """

        objects = set()
        paths = [os.path.join(self.pairtree_root, x) for x in os.listdir(self.pairtree_root) if os.path.isdir(os.path.join(self.pairtree_root, x))]
        d = None
        terminator = ppath.get_terminator(self.shorty_length)
        if paths:
            d = paths.pop()
        while d:
            for t in os.listdir(d):
                if t == terminator:
                    potential_id = self._get_id_from_dirpath(os.path.join(d, terminator))
                    if potential_id not in objects:
                        objects.add(potential_id)
                        yield potential_id
                elif os.path.isdir(os.path.join(d, t)):
                    paths.append(os.path.join(d, t))
            if paths:
                d = paths.pop()
            else:
                d =False

    def _create(self, id):
        """
        Internal - create an object. If the object already exists, raise a
        L{ObjectAlreadyExistsException}

        @param id: Identifier to be created
        @type id: identifier
        @returns: L{PairtreeStorageObject}
        """
        id = self._rm_uribase(id)
        dirpath = os.path.join(self._id_to_dirpath(id))
        if not os.path.exists(dirpath):
            os.makedirs(dirpath)
        else:
            raise ObjectAlreadyExistsException
        return PairtreeStorageObject(id, self)

    def list_parts(self, id, path=None):
        """
        List all the parts of the given identifer's parts (excluding shortie directories
        belonging to other objects)

        If path is supplied, the parts in that subdirectory are returned.

        If the subpath doesn't exist, a L{ObjectNotFoundException} will be raised.

        >>> store.list_parts('foobar:1', 'data/images')
        [ 'image001.tif', 'image....    ]

        @param id: Identifier for pairtree object
        @type id: identifier
        @param path: (Optional) List the parts contained in C{path}'s subdirectory
        @type path: Directory path
        @returns: L{list}
        """
        dirpath = os.path.join(self._id_to_dirpath(id))
        if path:
            dirpath = os.path.join(self._id_to_dirpath(id), path)
        if not os.path.exists(dirpath):
            raise ObjectNotFoundException
        return os.listdir(dirpath)
        #return [x for x in os.listdir(dirpath) if len(x)>self.shorty_length]

    def isfile(self, id, filepath):
        """
        Returns True or False depending on whether the path is a file or not.
        
        If the file doesn't exist, False is returned.
        
        @param filepath: Path to be tested
        @type filepath: Directory path
        @returns: L{bool}
        """
        dirpath = os.path.join(self._id_to_dirpath(id), filepath)
        try:
            return os.path.isfile(dirpath)
        except OSError:
            return False
        
    def isdir(self, id, filepath):
        """
        Returns True or False depending on whether the path is a subdirectory or not.
        
        If the path doesn't exist, False is returned.
        
        @param filepath: Path to be tested
        @type filepath: Directory path
        @returns: L{bool}
        """
        dirpath = os.path.join(self._id_to_dirpath(id), filepath)
        try:
            return os.path.isdir(dirpath)
        except OSError:
            return False
    
    def stat(self, id, filepath):
        """
        Returns the os.stat for a given file, or False if the file doesn't exist
        
        @param id: id of the object
        @type id: string
        @param filepath: Path to be tested
        @type filepath: Directory path
        @returns L{posix.stat_result} or False
        """
        if self.isfile(id, filepath):
            return os.stat(os.path.join(self._id_to_dirpath(id), filepath))
        else:
            return False

    def put_stream(self, id, path, stream_name, bytestream, buffer_size = 1024 * 64):
        """
        Store a stream of bytes into a file within a pairtree object.

        Can be either a string of bytes, or a filelike object which supports
        bytestream.read(buffer_size) - useful for very large files.

        @param id: Identifier for the pairtree object to write to
        @type id: identifier
        @param path: (Optional) subdirectory path to store file in
        @type path: Directory path
        @param stream_name: Name of the file to write to
        @type stream_name: filename
        @param bytestream: Either a string or a file-like object to read from
        @type bytestream: string|file
        @param buffer_size: (Optional) Used for streaming filelike objects - defines the size of the buffer
        to read in each cycle.
        @type buffer_size: integer
        @returns: tuple C{(hashing_algorithm, hash)} or None if hashing is disabled
        """
        dirpath = os.path.join(self._id_to_dirpath(id))
        if path:
            dirpath = os.path.join(self._id_to_dirpath(id), path)
        if not os.path.exists(dirpath):
            os.makedirs(dirpath)
        f = open(os.path.join(dirpath, stream_name), "wb")
        if self.hashing_type != None:
            hash_gen = getattr(hashlib, self.hashing_type)()
        try:
            # Stream file-like objects in with buffered reads
            if hasattr(bytestream, 'read'):
                try:
                    # try to get the stream back to zero
                    bytestream.seek(0)
                except:
                    pass
                if not buffer_size:
                    buffer_size = 1024 * 64
                chunk = bytestream.read(buffer_size)
                while chunk:
                    f.write(chunk)
                    if self.hashing_type != None:
                        hash_gen.update(chunk)
                    chunk = bytestream.read(buffer_size)
            else:
                f.write(bytestream)
                if self.hashing_type != None:
                    hash_gen.update(bytestream)
        except Exception, e:
            logger.info("put_stream failed: %s" % e)
        f.close()
        if self.hashing_type != None:
            return {"checksum":hash_gen.hexdigest(), "type":self.hashing_type}

    def get_appendable_stream(self, id, path, stream_name):
        """
        Reads a filehandle for a pairtree object. This is a "ab+" opened file and
        so can be appended to and obeys 'seek'
        
        >>> with store.get_appendable_stream('foobar:1','data/images', 'image001.tif') as stream:
                # Do something with the C{stream} handle
                pass

        stream is closed at the end of a C{with} block

        @param id: Identifier for the pairtree object to read from
        @type id: identifier
        @param path: (Optional) subdirectory path to retrieve file from
        @type path: Directory path
        @param stream_name: Name of the file to read in
        @type stream_name: filename
        @returns: L{file}
        """
        file_path = os.path.join(self._id_to_dirpath(id), stream_name)
        if path:
            file_path = os.path.join(self._id_to_dirpath(id), path, stream_name)
        f = open(file_path, "ab+")
        return f

    def get_url(self, id, stream_name, path=None):
        """
        Returns a direct 'file:///...' URL for a given id and stream (with an optional path)

        @param id: Identifier for the pairtree object to read from
        @type id: identifier
        @param path: (Optional) subdirectory path to the file location
        @type path: Directory path
        @param stream_name: Name of the file to point to
        @type stream_name: filename
        @returns: L{str} - eg "file:///opt/store/pairtree_root/..../foo.txt"
        """
        file_path = stream_name
        if path:
            file_path = os.path.join(path, stream_name)
        url_prefix = ppath.id_to_url(self._rm_uribase(id), self.pairtree_root, self.shorty_length)
        return os.sep.join((url_prefix, file_path))

    def get_stream(self, id, path, stream_name, streamable=False):
        """
        Reads a file from a pairtree object - If streamable is set to True,
        this returns the filehandle for that file, which must be C{close()}'d
        once finished with. In python 2.6 and above, this can be done easily:

        >>> with store.get_stream('foobar:1','data/images', 'image001.tif', True) as stream:
                # Do something with the C{stream} handle
                pass

        stream is closed at the end of a C{with} block

        @param id: Identifier for the pairtree object to read from
        @type id: identifier
        @param path: (Optional) subdirectory path to retrieve file from
        @type path: Directory path
        @param stream_name: Name of the file to read in
        @type stream_name: filename
        @param streamable: If True, returns a filelike handle to C{read()} from -
        I{remember to C{close()} the file!} If False, reads in the file into a
        bytestring and return that instead.
        @type streamable: True|False
        @returns: Either L{file} or L{str}
        """
        file_path = os.path.join(self._id_to_dirpath(id), stream_name)
        if path:
            file_path = os.path.join(self._id_to_dirpath(id), path, stream_name)
        if not os.path.exists(file_path):
            raise PartNotFoundException(id=id, path=path, stream_name=stream_name,file_path=file_path)
        f = open(file_path, "rb")
        if streamable:
            return f
        else:
            bytestream = f.read()
            f.close()
            return bytestream

    def del_stream(self, id, stream_name, path=None):
        """
        Delete a file from a pairtree object. Leaves no trace, be careful.
        @param id: Identifier for the pairtree object to delete from
        @type id: identifier
        @param path: (Optional) subdirectory path to delete file from
        @type path: Directory path
        @param stream_name: Name of the file to delete
        @type stream_name: filename
        """
        file_path = os.path.join(self._id_to_dirpath(id), stream_name)
        if path:
            file_path = os.path.join(self._id_to_dirpath(id), path, stream_name)
        if not os.path.exists(file_path):
            raise PartNotFoundException(id=id, path=path, stream_name=stream_name,file_path=file_path)
        if os.path.isdir(file_path):
            os.rmdir(file_path)
            isdir = True
        else:
            os.remove(file_path)
             
    def del_path(self, id, path, recursive=False):
        """
        Delete a subpath from an object, and can do so recursively (optional)
        If the path is found to be not "empty" (ie has not parts in it) and
        recursive is not True, then it will raise a L{PathIsNotEmptyException}
        @param id: Identifier for the pairtree object to delete from
        @type id: identifier
        @param path: subdirectory path to delete
        @type path: Directory path
        @param recursive: Whether the delete is recursive (think rm -r)
        @type recursive: bool
        """
        dirpath = os.path.join(self._id_to_dirpath(id), path)
        if not os.path.exists(dirpath):
            raise PartNotFoundException
        if os.path.isfile(dirpath):
            os.remove(dirpath)
        else:
            # It's a directory:
            all_parts = os.listdir(dirpath)
            
            if len(all_parts) == 0:
                os.rmdir(dirpath)
            elif recursive:
                # thankfully, terminators simplify this
                shutil.rmtree(dirpath)
            else:
                raise PathIsNotEmptyException

    def delete_object(self, id):
        """
        Delete's an object from the pairtree store, including any parts and subpaths
        There is no undo...
        @param id: Identifier of the object to delete
        @type id: identifier
        """
        dirs = self._id_to_dir_list(id)
        dirpath = os.path.join(os.sep.join(dirs))
        if not os.path.exists(dirpath):
            raise ObjectNotFoundException
        for item in self.list_parts(id):
            self.del_path(id,item, recursive=True)
        if not os.listdir(dirpath):
            os.rmdir(dirpath)
        # recursively delete up, if the directory is empty
        leaf = dirs.pop()
        while (not os.listdir(os.sep.join(dirs)) and os.sep.join(dirs) != self.pairtree_root):
            os.rmdir(os.sep.join(dirs))
            dirs.pop()

    def exists(self, id, path=None):
        """
        Answers the question "Does object or object subpath/file 'xxxxxxx' exist?"

        @param id: Identifier for the pairtree object to look for
        @type id: identifier
        @param path: Subpath or subfilepath to check
        @type path: Directory path
        @returns: L{bool}
        """
        dirpath = os.path.join(self._id_to_dirpath(id))
        if path:
            dirpath = os.path.join(self._id_to_dirpath(id), path)
        return os.path.exists(dirpath)

    def _get_new_id(self):
        """
        Inbuilt method to randomly generate an id, if one is not given to either
        L{get_object} or L{create_object}.

        Simply returns a random 14 digit long (base 10) number, not fantastically useful
        but at least makes sure it is unique in the store.

        @returns: Random but unique 14-digit long id number
        """
        id = "%.14d" % random.randint(0,99999999999999)
        while self.exists(id):
            id = "%.14d" % random.randint(0,99999999999999)
        return id

    def get_object(self, id=None, create_if_doesnt_exist=True):
        """
        Returns an pairtree object with identifier C{id} if it exists.

        If the object at C{id} doesn't exist then depending on C{create_if_doesnt_exist},

        >>> bar = client.get_object('bar')
        # the object with id 'bar' will be retrieved and created if necessary.

        Setting this flag to False, will cause it to raise an exception if it cannot find an object.

        >>> fake = client.get_object('doesnotexist', create_if_doesnt_exist=False)
        Traceback (most recent call last):
          File "<stdin>", line 1, in <module>
          File "build/bdist.linux-i686/egg/pairtree/pairtree_client.py", line 231, in get_object
        pairtree.storage_exceptions.ObjectNotFoundException

        (note that fake = client.get_object('doesnotexist', False) is equivalent to the above line)

        @param id: Identifier for the pairtree object to get (or create)
        @type id: identifier
        @param create_if_doesnt_exist: Flag - if True, an object will be created if it
        doesn't yet exist. Will raise an L{ObjectNotFoundException} if set to False
        and the object is non-existent.
        @type create_if_doesnt_exist: True|False
        @returns: L{PairtreeStorageObject}
        """
        if not id:
            id = self._get_new_id()
            return self._create(id)
        
        id = self._rm_uribase(id)
             
        if self.exists(id):
            return PairtreeStorageObject(id, self)
        elif create_if_doesnt_exist:
            return self._create(id)
        else:
            raise ObjectNotFoundException

    def create_object(self, id):
        """
        Creates a new object with identifier C{id}

        >>> bar = client.create_object('bar')
        >>>

        Note that reissuing that command again will raise an L{ObjectAlreadyExistsException}:

        >>> bar = client.create_object('bar')
        Traceback (most recent call last):
          File "<stdin>", line 1, in <module>
          File "build/bdist.linux-i686/egg/pairtree/pairtree_client.py", line 235, in create_object
        pairtree.storage_exceptions.ObjectAlreadyExistsException

        @param id: Identifier for the pairtree object to create
        @type id: identifier
        @returns: L{PairtreeStorageObject}
        """
        return self._create(id)

