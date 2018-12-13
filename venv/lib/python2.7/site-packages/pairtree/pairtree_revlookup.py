#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
FS Pairtree storage - Reverse lookup
====================================

Conventions used:

From http://www.cdlib.org/inside/diglib/pairtree/pairtreespec.html version 0.1

This is an implementation of a reverse lookup index, using the pairtree path spec to 
record the link between local id and the id's that it corresponds to.

eg to denote issn:1234-1234 as being linked to a global id of "uuid:1e4f..."

-->  create a file at ROOT_DIR/pairtree_rl/is/sn/+1/23/4-/12/34/uuid+1e4f...

Note that the id it links to is recorded as a filename encoded as per the pairtree spec.

Usage
=====

>>> from pairtree import PairtreeReverseLookup
>>> rl = PairtreeReverseLookup(storage_dir="ROOT")

>>> rl["issn:1234-1234"].append("uuid:1e4f...")

>>> rl["issn:1234-1234"]
["uuid:1e4f"]

>>> rl["issn:1234-1234"] = ["id:1", "uuid:32fad..."]
>>>

Notes
=====

This was created to avoid certain race conditions I had with a pickled dictionary for this index.
A sqllite or similar lookup would also be effective, but this one relies solely on pairtree.
"""

from __future__ import with_statement

import os

from pairtree_path import id_encode, id_decode, get_id_from_dirpath, get_path_from_dirpath, id_to_dirpath

PAIRTREE_RL = "pairtree_rl"

class PairtreeReverseLookup_list(object):
  def __init__(self, rl_dir, id):
    self._rl_dir = rl_dir
    self._id = id
    self._dirpath = id_to_dirpath(self._id, self._rl_dir)
  
  def _get_ids(self):
    if os.path.isdir(self._dirpath):
      ids = []
      for f in os.listdir(self._dirpath):
        ids.append(id_decode(f))
      return ids
    else:
      return []
  
  def _add_id(self, new_id):
    if not os.path.exists(self._dirpath):
      os.makedirs(self._dirpath)
    enc_id = id_encode(new_id)
    if not os.path.isfile(enc_id):
      with open(os.path.join(self._dirpath, enc_id), "w") as f:
        f.write(new_id)
  
  def _exists(self, id):
    if os.path.exists(self._dirpath):
      return id_encode(id) in os.listdir(self._dirpath)
    else:
      return False
  
  def append(self, *args):
    [self._add_id(x) for x in args if not self._exists(x)]
  
  def __len__(self):
    return len(os.listdir(self._dirpath))
  
  def __repr__(self):
    return "ID:'%s' -> ['%s']" % (self._id, "','".join(self._get_ids()))
  
  def __str__(self):
    return self.__repr__()
  
  def __iter__(self):
    for f in self._get_ids():
      yield id_decode(f)
    
class PairtreeReverseLookup(object):
  def __init__(self, storage_dir="data"):
    self._storage_dir = storage_dir
    self._rl_dir = os.path.join(storage_dir, PAIRTREE_RL)
    self._init_store()
  
  def _init_store(self):
    if not os.path.isdir(self._storage_dir):
      os.makedirs(self._storage_dir)
  
  def __getitem__(self, id):
    return PairtreeReverseLookup_list(self._rl_dir, id)
  
  def __setitem__(self, id, value):
    id_c = PairtreeReverseLookup_list(self._rl_dir, id)
    if isinstance(list, value):
      id_c.append(*value)
    else:
      id_c.append(value)

  def __delitem__(self, id):
    dirpath = id_to_dirpath(id, self._rl_dir)
    if os.path.isdir(dirpath):
      for f in os.listdir(dirpath):
        os.remove(os.path.join(dirpath, f))
      os.removedirs(dirpath)  # will throw OSError if the dir cannot be removed.
      self._init_store() # just in case
