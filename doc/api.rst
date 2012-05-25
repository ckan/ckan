.. index:: API
.. _api:

========
CKAN API
========

.. toctree::
   :hidden:
   :maxdepth: 1

The CKAN platform is not only available in a web browser, but also via its
Application Programming Interface (API). The API provides programmatic access
to the CKAN system. The API is very powerful and allows you do everything (and more) you can do via the web interface.

Using the API you can do things like:

* Access any bit of information in CKAN (if you are authorized!)
* Edit any piece of information in CKAN
* Create a whole new web front-end for CKAN (if you want!)

The CKAN API follows the RESTful (Representational State Transfer) style and
uses JSON by default.

.. _tools-for-api:

Tools for Accessing the API
===========================

In using the API you will be performing HTTP requests to urls like: ``/api/rest/dataset`` with this returning data in JSON format.

There are several ways you can access this URL directly:

* Put this URL into your web browser and view or save the resulting response -- there are plugins for browsers like Firefox and Chrome that allow you to see JSON nicely formatted in your browser (e.g. `JSONView for Chrome <https://chrome.google.com/webstore/detail/chklaanhfefbnpoihckbnefhakgolnmc>`_)
* Use a command-line program such as `curl <http://curl.haxx.se/>`_
* Write a program in your favourite language that uses an http library to access the URL

Clients
-------

Alternatively, you can access the API using one the dedicated tools or libraries written specifically for CKAN. The following clients are available:

* `dpm (data package manager) <http://github.com/okfn/dpm/>`_: command-line client and Python library (maintained by core CKAN team)
* `ckanclient - CKAN Python Client <http://pypi.python.org/pypi/ckanclient>`_: Python client maintained by the core CKAN team
* `CKAN Ruby <https://github.com/apohllo/ckan>`_: Ruby Client
* `Ckan_client-PHP <http://github.com/jeffreybarke/Ckan_client-PHP>`_: PHP client
* `Ckan_client-J <https://github.com/okfn/ckanclient-j>`_: Java client
* `net-ckan <http://github.com/lukec/net-ckan>`_: PERL client
* `ckanjs <http://github.com/okfn/ckanjs>`_: sophisticated Javascript client built on Backbone.
* `Google Refine CKAN Extension <http://ckan.org/2011/07/05/google-refine-extension-for-ckan/>`_: Google Refine client which allows you to get and push data to and from a CKAN instance using Google Refine.

Quickstart Tutorial
===================

.. toctree::
   :maxdepth: 2

   api-tutorial.rst

.. _api-keys:

Authentication and API Keys
===========================

CKAN can be configured to only allow authorized users to carry out certain
actions (see :doc:`authorization` for more details). The authorization
configuration is the same for actions done over the API as for those carried
out in the CKAN web interfac, so a user has the same permissions, whichever way
he/she accesses CKAN data.

Thus, all actions **not** permitted to anonymous users, will require a user to
identify themselves via some authentication method.

.. note:: Depending on the authorization settings of the CKAN instance, a user
          may need to authenticate themselves for all operations including
          read. However, by default, CKAN allows anonymous read access and this
          setup is assumed for the API usage examples.

The standard authentication method utilized by CKAN is API keys and a user
authenticates his/her user identity by supplying a header in the request
containing the API key. The header field is either ``Authorization``,
``X-CKAN-API-Key`` or configured with the `apikey_header_name` option. (Details
of how to obtain an API key are below).

For example::

  curl http://thedatahub.org/api/rest/package -d '{"name": "test"}' -H 'Authorization: fde34a3c-b716-4c39-8dc4-881ba115c6d4'

If requests that are required to be authorized are not sent with a 
valid Authorization header, for example the user associated with the 
key is not authorized for the operation, or the header is somehow malformed,
then the requested operation will not be carried out and the CKAN API will
respond with status code 403.

.. _get-api-key:

Obtaining an API key
--------------------

1. Log-in to the particular CKAN website: ``/user/login``

2. Your user page will show the API Key in your details section at the top of the screen

JSONP Support
=============

To cater for scripts from other sites that wish to access the API, the data can be returned in JSONP format, where the JSON data is 'padded' with a function call. The function is named in the 'callback' parameter.

Example normal request::

 GET /api/rest/dataset/pollution_stats
 returns: {"name": "pollution_stats", ... }

but now with the callback parameter::

 GET /api/rest/dataset/pollution_stats?callback=name-of-callback-function
 returns: jsoncallback({"name": "pollution_stats", ... });

This parameter can apply to all POST requests to the Action API and GET requests to the Search API and v1/v2/v3 APIs.

.. _api-reference: 

API: Reference
==============

Model, Search and Actions APIs
------------------------------

These sections describe the resource locations, data formats, and status codes
which comprise the CKAN API.

The CKAN API is versioned, so that backwards incompatible changes can be
introduced without removing existing support. A particular version of the API
can be used by including its version number after the API location and before
the resource location.

If the API version is not specified in the request, then the API will default
to version 1.

Version 1 and 2 
~~~~~~~~~~~~~~~

.. toctree::
   :maxdepth: 2

   api-v2.rst

Version 3
~~~~~~~~~

This version is in beta.

.. toctree::
   :maxdepth: 2

   apiv3.rst

Util API
--------

The Util API provides various utility APIs -- e.g. auto-completion APIs used by
front-end javascript.

.. toctree::
   :maxdepth: 2

   api-util.rst

