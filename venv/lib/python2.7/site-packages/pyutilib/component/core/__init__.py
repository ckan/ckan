#  _________________________________________________________________________
#
#  PyUtilib: A Python utility library.
#  Copyright (c) 2008 Sandia Corporation.
#  This software is distributed under the BSD License.
#  Under the terms of Contract DE-AC04-94AL85000 with Sandia Corporation,
#  the U.S. Government retains certain rights in this software.
#  _________________________________________________________________________

"""
The outline of the PyUtilib Component Architecture (PCA) is adapted from Trac (see
the trac.core module).  This framework generalizes the Trac by supporting
multi-environment management of components, as well as non-singleton plugins.

This package provides a stand-alone module that defines all of the core
aspects of the PCA.  Related Python packages define extensions of this
framework that support current component-based applications.

NOTE: The PCA does not rely on any other part of PyUtilib.  Consequently,
this package can be independently used in other projects.
"""

import sys
from pyutilib.component.core.core import *

PluginGlobals.push_env("pca")

#
# This declaration is here because this is a convenient place where
# all symbols in this module have been defined.
#

class IgnorePluginPlugins(SingletonPlugin):
    """Ignore plugins from the pyutilib.component module"""

    implements(IIgnorePluginWhenLoading)

    def ignore(self, name):
        return name in list(globals().keys())


#
# Import the 'pyutilib.component' plugins
#
try:
    import pkg_resources
    #
    # Load modules associated with Plugins that are defined in
    # EGG files.
    #
    for entrypoint in pkg_resources.iter_entry_points('pyutilib.component'):
        plugin_class = entrypoint.load()
        #print "Loading plugins... (%s)" % entrypoint
except ImportError:
    pass
except Exception:
    import sys
    err = sys.exc_info()[1]
    from sys import stderr as SE
    SE.write( "Error loading 'pyutilib.component' entry points: '%s'\n" % err )

#
# Remove the "pca" environment as the default
#
PluginGlobals.pop_env()
