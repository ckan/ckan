class ObjectNotFoundException(Exception):
    """Object not found at the ID specified"""
    pass

class FileNotFoundException(Exception):
    """File cannot be found at the location requested"""
    pass

class PartNotFoundException(Exception):
    """Part not found"""
    def __init__(self, *p, **kw):
        self.context = (p, kw)
    def __str__(self):
        print " - Part not found: %s" % self.context

class StoreNotFoundException(Exception):
    """Store not found"""
    pass

class ObjectAlreadyExistsException(Exception):
    """Object ID already exists"""
    pass

class StoreAlreadyExistsException(Exception):
    """Store ID already exists"""
    pass

class PathIsNotEmptyException(Exception):
    """Cannot remove a path that isn't empty without the recursive flag set'"""
    pass

class NotAPairtreeStoreException(Exception):
    """The directory indicated exists, but doesn't
    announce itself to be a pairtree store via a
    'pairtree_version0_1' marker file in the root."""

class NotAValidStoreName(Exception):
    """Invalid name for a store. Must conform to ^[A-z][A-z0-9]* regex"""

