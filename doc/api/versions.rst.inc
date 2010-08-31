API Versions
============

The CKAN API is versioned, so that backwards incompatible changes can be
introduced without removing existing support. A resource location for a
particular version can be formed by inserting the version number between the API location and the resource path, like this:

  API_LOCATION + "/" + API_VERSION + RESOURCE_LOCATION

If a request does not specify an API version, then the API will use the oldest
supported version of the API to handle that request. The oldest supported
version is currently 1.


CKAN API Version 1
------------------

The :doc:`api/1/index` is the original CKAN API.

Packages are identified by name in entity representations.

CKAN API Version 2
------------------

The :doc:`api/2/index` is the latest CKAN API.

Packages are identified by id in entity representations.

CKAN API Version 3
------------------

The :doc:`api/3/index` is the next CKAN API, and is currently unstable. Some resource locations have been changed.

