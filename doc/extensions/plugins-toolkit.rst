.. py:module:: ckan.plugins.toolkit

-------------------------
Plugins toolkit reference
-------------------------

As well as using the variables made available to them by implementing plugin
interfaces, plugins will likely want to be able to use parts of the CKAN core
library. To allow this, CKAN provides a stable set of classes and functions
that plugins can use safe in the knowledge that this interface will remain
stable, backward-compatible and with clear deprecation guidelines when new
versions of CKAN are released. This interface is available in CKAN's *plugins
toolkit*.


