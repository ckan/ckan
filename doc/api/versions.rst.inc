.. |oldest_version| replace:: 1

Versions
--------

The |site| |api| is versioned, so that backwards incompatible changes can be
introduced without removing existing support.  A particular version of the API
can be used by including its version number after the API location and before
the resource location.

If the API version is not included in the request, then the API will use the 
oldest supported version of the API to handle that request. The oldest supported
version is currently |oldest_version|.


Version 1
~~~~~~~~~

The |version_1_doc| is the original API. At first, package and group names were invariant, and were used in persistent references.

Version 2
~~~~~~~~~

The |version_2_doc| is the latest API. Since edting the names of packages and groups is now possible, packages and groups are identified by their UUID in entity representations.

Version 3
~~~~~~~~~

The |version_3_doc| is the next CKAN API, and is currently unstable. Various resource locations are being changed to consolidate the interface design and help simplify the documentation and client implementations.

