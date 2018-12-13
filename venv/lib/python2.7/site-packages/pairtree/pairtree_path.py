#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Conventions used:

From http://www.cdlib.org/inside/diglib/pairtree/pairtreespec.html version 0.1

This client handles all of the pairtree conventions, and provides a Pairtree object
to make it easier to interact with.

+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

EXTENSION - This version uses terminators to signal the directory within which an object resides. This
is an effort to avoid the 'split-end' issue and to simplify a number of issues to do with object file and subpath
listings.

So:

foobar:1/ goes to fo/ob/ar/+1/obj/

and 

bar:1/subpath/manifest.rdf goes to ba/r+/1/obj/subpath/manifest.rdf

+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

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

import logging

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger('pairtreepath')

encode_regex = re.compile(r"[\"*+,<=>?\\^|]|[^\x21-\x7e]", re.U)
decode_regex = re.compile(r"\^(..)", re.U)

def char2hex(m):
        return "^%02x"%ord(m.group(0))

def hex2char(m):
        return chr(int(m.group(1), 16))


def id_encode(id):
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
            ->  ar/k+/=1/30/30/=x/t1/2t/3/obj/
        id:  http://n2t.info/urn:nbn:se:kb:repos-1
            ->  http+==n2t,info=urn+nbn+se+kb+repos-1
            ->  ht/tp/+=/=n/2t/,i/nf/o=/ur/n+/n/bn/+s/e+/kb/+/re/p/os/-1/obj/
        id:  what-the-*@?#!^!?
            ->  what-the-^2a@^3f#!^5e!^3f
            ->  wh/at/-t/he/-^/2a/@^/3f/#!/^5/e!/^3/f/obj/

    (From section 3 of the Pairtree specification - with obj extension)

    @param id: Encode the given identifier according to the pairtree 0.1 specification
    @type id: identifier
    @returns: A string of the encoded identifier
    """
    # Unicode or bust
    if isinstance(id, unicode):
        # assume utf-8
        # TODO - not assume encoding
        id = id.encode('utf-8')

    second_pass_m = {'/':'=',
                        ':':'+',
                        '.':','
                    }
    # hexify the odd characters
    # Using Erik Hetzner's regex in place of my previous hack
    new_id = encode_regex.sub(char2hex, id)
    
    # 2nd pass
    second_pass = []
    for char in new_id:
        second_pass.append(second_pass_m.get(char, char))
    return "".join(second_pass)

def id_decode(id):
    """
    This decodes a given identifier from its pairtree filesystem encoding, into
    its original form:
    @param id: Identifier to decode
    @type id: identifier
    @returns: A string of the decoded identifier
    """
    second_pass_m = {'=':'/',
                        '+':':',
                        ',':'.'
                    }
    second_pass = []
    for char in id:
        second_pass.append(second_pass_m.get(char, char))
    dec_id = "".join(second_pass)
    #dec_id = id.translate(string.maketrans(u'=+,',u'/:.'))
    # Using Erik Hetzner's regex in place of my previous hack
    #ppath_s = re.sub(r"\^(..)", self.__hex2char, dec_id)
    ppath_s = decode_regex.sub(hex2char, dec_id)
    # Again, drop the assumption of utf-8
    return ppath_s.decode('utf-8')

def get_terminator(shorty_length=2, end_of_pairtree_path="obj"):
    """
    Terminator directory name, based on the shorty length.
    
    It has to be one greater than the shorty length of a given pairtree, to avoid being
    part of a splitend and potentially incorporated or interpreted as part of another object
    
    shorty length = 1 (with default end of path string)
    -> "ob"
    shorty length = 2
    -> "obj"
    shorty length = 6
    -> "objobjo"
    """
    return "".join([(end_of_pairtree_path[x % len(end_of_pairtree_path)]) for x in xrange(shorty_length+1)])

def get_id_from_dirpath(dirpath, pairtree_root=""):
    """
    Internal - method for discovering the pairtree identifier for a
    given directory path.

    E.g.  pairtree_root/fo/ob/ar/+/  --> 'foobar:'

    @param dirpath: Directory path to decode
    @type dirpath: Path to object's root
    @returns: Decoded identifier
    """
    path, shorty_length = get_path_from_dirpath(dirpath, pairtree_root)
    assert path[-1] == get_terminator(shorty_length=shorty_length)
    return id_decode("".join(path[:-1]))

def get_path_from_dirpath(dirpath, pairtree_root=""):
    """
    Internal - walks a directory chain and builds a list of the directory shorties
    relative to the pairtree_root

    @param dirpath: Directory path to walk
    @type dirpath: Directory path
    """
    shorty_length = None
    head, tail = os.path.split(dirpath)
    path = [tail]
    while not pairtree_root == head:
        head, tail = os.path.split(head)
        shorty_length = len(tail)
        path.append(tail)
    path.reverse()
    try:
        assert path[-1] == get_terminator(shorty_length=shorty_length)
    except AssertionError:
        if len(path) == 2:
            # edge case - id length of 1. Using the terminator length as (shorty_length+1)
            shorty_length = len(path[-1])-1
        else:
            logger.error("For dirpath: %s and pairtree_root=%s" % (dirpath, pairtree_root))
            logger.error("Anticipated to get an %s at the end of the path, got %s instead" % (get_terminator(shorty_length=shorty_length), path) )
    return path, shorty_length

def id_to_dirpath(id, pairtree_root="", shorty_length=2):
    """
    Internal - method for turning an identifier into a pairtree directory tree
    of shorties.

        -  I{"foobar://ark.1" --> "fo/ob/ar/+=/ar/k,/1"}

    @param id: Identifer for a pairtree object
    @type id: identifier
    @returns: A directory path to the object's root directory
    """
    return os.sep.join(id_to_dir_list(id, pairtree_root, shorty_length))

def id_to_url(id, pairtree_root, shorty_length=2):
    """Method to provide 'file:///..../pairtree_root/...' URLs pointing at a given object.

        -  I{"foobar" --> "file:///opt/pairtree_root/fo/ob/ar/obj"}

    @param id: Identifier for a pairtree object
    @type id: identifier
    @param pairtree_root: required path to the pairtree store (and must exist)
    @returns: A 'file:///' URL
    """
    if os.path.isdir(pairtree_root):
        root = os.path.abspath(pairtree_root)
        obj_path = id_to_dirpath(id, shorty_length = shorty_length)
        return "file://%s" % (os.path.join(root, obj_path))
    else:
        raise OSError, "pairtree_root '' does not exist." % pairtree_root


def id_to_dir_list(id, pairtree_root="", shorty_length=2):
    """
    Internal - method for turning an identifier into a list of pairtree 
    directory tree of shorties.

        -  I{"foobar://ark.1" --> ["fo","ob","ar","+=","ar","k,","1"]}

    @param id: Identifer for a pairtree object
    @type id: identifier
    @returns: A list of directory path fragments to the object's root directory
    """
    enc_id = id_encode(id)
    dirpath = []
    if pairtree_root:
        dirpath = [pairtree_root]
    while enc_id:
        dirpath.append(enc_id[:shorty_length])
        enc_id = enc_id[shorty_length:]
    dirpath.append(get_terminator(shorty_length=shorty_length))
    return dirpath

