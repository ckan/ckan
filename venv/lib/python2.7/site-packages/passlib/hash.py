"""passlib.hash - proxy object mapping hash scheme names -> handlers

Note
====
This module does not actually contain any hashes. This file
is a stub that replaces itself with a proxy object.

This proxy object (passlib.registry._PasslibRegistryProxy)
handles lazy-loading hashes as they are requested.

The actual implementation of the various hashes is store elsewhere,
mainly in the submodules of the ``passlib.handlers`` package.
"""

# NOTE: could support 'non-lazy' version which just imports
#       all schemes known to list_crypt_handlers()

#=============================================================================
# import proxy object and replace this module
#=============================================================================

from passlib.registry import _proxy
import sys
sys.modules[__name__] = _proxy

#=============================================================================
# eoc
#=============================================================================
