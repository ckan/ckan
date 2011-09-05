.. index:: API

===========================
Reference: CKAN API
===========================

.. toctree::
   :hidden:
   :maxdepth: 1

The CKAN API provides programmatic access to the catalog of metadata stored in CKAN.

Overview
--------

The CKAN data catalog is not only available in a web browser, but also
via its Application Programming Interface (API).

The API can be used to view and change the catalog. This document describes the 
resource locations, data formats, and status codes which comprise the CKAN
API, so that anyone can create software applications that use the API
service.

The CKAN API follows the RESTful (Representational State 
Transfer) style. Resource locations are separated both from the methods
supported by the resources, and from the data formats and status codes
used by the methods.

Examples
--------

For a tutorial and examples of using the CKAN API, see: http://wiki.ckan.net/Using_the_API

Code Modules for Client Applications
-------------------------------------

There are also some code modules (Python, PHP, Drupal, Perl etc.) that provide 
convenient wrappers around much of the CKAN API. For full details of these, 
please consult http://wiki.ckan.net/API

Versions
--------

The CKAN API is versioned, so that backwards incompatible changes can be
introduced without removing existing support.  A particular version of the API
can be used by including its version number after the API location and before
the resource location.

If the API version is not specified in the request, then the API will default to version 1.

Versions 1 & 2
~~~~~~~~~~~~~~

These are very similar, but when the API returns a reference to an object, Version 1 API will return the Name of the object (e.g. "river-pollution") and Version 2 API will return the ID of the object (e.g. "a3dd8f64-9078-4f04-845c-e3f047125028").

The reason for this is that Names can change, so to reliably refer to the same dataset every time, you will want to use the ID and therefore use API v2. Alternatively, many people prefer to deal with Names, so API v1 suits them.

When making requests, you can call objects by either their Name or ID, interchangeably.

The only exception for this is for Tag objects. Since Tag names are immutable, they are always referred to with their Name.


API Details - Versions 1 & 2
----------------------------

Overview
~~~~~~~~

The CKAN data catalog is not only available in a web browser, but also
via its Application Programming Interface (API).

The API can be used to view and change the catalog. This document describes the 
resource locations, data formats, and status codes which comprise the CKAN
API, so that anyone can create software applications that use the API
service.

The CKAN API follows the RESTful (Representational State 
Transfer) style. Resource locations are separated both from the methods
supported by the resources, and from the data formats and status codes
used by the methods.


The CKAN API version 1 & 2 is separated into three parts.

* `Model API`_
* `Search API`_
* `Util API`_

The resources, methods, and data formats of each are described below.

Locators
~~~~~~~~

The locator for a given resource can be formed by appending
the relative path for that resource to the API locator.

  ``Resource Locator = API Locator + Resource Path``

The API locators for the CKAN APIs (by version) are:

 * ``http://ckan.net/api`` (version 1)
 * ``http://ckan.net/api/1`` (version 1)
 * ``http://ckan.net/api/2`` (version 2)

The relative paths for each resource are listed in the sections below.

Model API
~~~~~~~~~

Model resources are available at published locations. They are represented with
a variety of data formats. Each resource location supports a number of methods.

The data formats of the requests and the responses are defined below.

Model Resources
```````````````

Here are the resources of the Model API.


+--------------------------------+-------------------------------------------------------------------+
| Model Resource                 | Location                                                          |
+================================+===================================================================+
| Dataset Register               | ``/rest/dataset``                                                 |
+--------------------------------+-------------------------------------------------------------------+
| Dataset Entity                 | ``/rest/dataset/DATASET-REF``                                     |
+--------------------------------+-------------------------------------------------------------------+
| Group Register                 | ``/rest/group``                                                   |
+--------------------------------+-------------------------------------------------------------------+
| Group Entity                   | ``/rest/group/GROUP-REF``                                         |
+--------------------------------+-------------------------------------------------------------------+
| Tag Register                   | ``/rest/tag``                                                     |
+--------------------------------+-------------------------------------------------------------------+
| Tag Entity                     | ``/rest/tag/TAG-NAME``                                            |
+--------------------------------+-------------------------------------------------------------------+
| Rating Register                | ``/rest/rating``                                                  |
+--------------------------------+-------------------------------------------------------------------+
| Dataset Relationships Register | ``/rest/dataset/DATASET-REF/relationships``                       |
+--------------------------------+-------------------------------------------------------------------+
| Dataset Relationships Register | ``/rest/dataset/DATASET-REF/RELATIONSHIP-TYPE``                   |
+--------------------------------+-------------------------------------------------------------------+
| Dataset Relationships Register | ``/rest/dataset/DATASET-REF/relationships/DATASET-REF``           |
+--------------------------------+-------------------------------------------------------------------+
| Dataset Relationship Entity    | ``/rest/dataset/DATASET-REF/RELATIONSHIP-TYPE/DATASET-REF``       |
+--------------------------------+-------------------------------------------------------------------+
| Dataset\'s Revisions Entity    | ``/rest/dataset/DATASET-REF/revisions``                           |
+--------------------------------+-------------------------------------------------------------------+
| Revision Register              | ``/rest/revision``                                                |
+--------------------------------+-------------------------------------------------------------------+
| Revision Entity                | ``/rest/revision/REVISION-ID``                                    |
+--------------------------------+-------------------------------------------------------------------+
| License List                   | ``/rest/licenses``                                                |
+--------------------------------+-------------------------------------------------------------------+

Possible values for DATASET-REF are the dataset id, or the current dataset name.

Possible values for RELATIONSHIP-TYPE are described in the Relationship-Type data format.


Model Methods
`````````````

Here are the methods of the Model API.

+-------------------------------+--------+------------------+-------------------+
| Resource                      | Method | Request          | Response          |
+===============================+========+==================+===================+ 
| Dataset Register              | GET    |                  | Dataset-List      |
+-------------------------------+--------+------------------+-------------------+
| Dataset Register              | POST   | Dataset          |                   |
+-------------------------------+--------+------------------+-------------------+
| Dataset Entity                | GET    |                  | Dataset           |
+-------------------------------+--------+------------------+-------------------+
| Dataset Entity                | PUT    | Dataset          |                   |
+-------------------------------+--------+------------------+-------------------+
| Group Register                | GET    |                  | Group-List        |
+-------------------------------+--------+------------------+-------------------+
| Group Register                | POST   | Group            |                   |
+-------------------------------+--------+------------------+-------------------+
| Group Entity                  | GET    |                  | Group             |
+-------------------------------+--------+------------------+-------------------+
| Group Entity                  | PUT    | Group            |                   |
+-------------------------------+--------+------------------+-------------------+
| Tag Register                  | GET    |                  | Tag-List          | 
+-------------------------------+--------+------------------+-------------------+
| Tag Entity                    | GET    |                  | Dataset-List      |
+-------------------------------+--------+------------------+-------------------+
| Rating Register               | POST   | Rating           |                   |
+-------------------------------+--------+------------------+-------------------+
| Rating Entity                 | GET    |                  | Rating            |
+-------------------------------+--------+------------------+-------------------+
| Dataset Relationships Register| GET    |                  | Pkg-Relationships |
+-------------------------------+--------+------------------+-------------------+
| Dataset Relationship Entity   | GET    |                  | Pkg-Relationship  |
+-------------------------------+--------+------------------+-------------------+
| Dataset Relationship Entity   | PUT    | Pkg-Relationship |                   |
+-------------------------------+--------+------------------+-------------------+
| Dataset\'s Revisions Entity   | GET    |                  | Pkg-Revisions     |
+-------------------------------+--------+------------------+-------------------+
| Revision List                 | GET    |                  | Revision-List     |
+-------------------------------+--------+------------------+-------------------+
| Revision Entity               | GET    |                  | Revision          |
+-------------------------------+--------+------------------+-------------------+
| License List                  | GET    |                  | License-List      |
+-------------------------------+--------+------------------+-------------------+

* POSTing data to a register resource will create a new entity.

* PUT/POSTing data to an entity resource will update an existing entity.

* PUT operations may instead use the HTTP POST method.

Model Formats
`````````````

Here are the data formats for the Model API.

.. |format-dataset-ref| replace:: Dataset-Ref

.. |format-dataset-register| replace:: [ |format-dataset-ref|, |format-dataset-ref|, |format-dataset-ref|, ... ]

.. |format-dataset-entity| replace:: { id: Uuid, name: Name-String, title: String, version: String, url: String, resources: [ Resource, Resource, ...], author: String, author_email: String, maintainer: String, maintainer_email: String, license_id: String, tags: Tag-List, notes: String, extras: { Name-String: String, ... } }

.. |format-group-ref| replace:: Group-Ref

.. |format-group-register| replace:: [ |format-group-ref|, |format-group-ref|, |format-group-ref|, ... ]

.. |format-group-entity| replace:: { name: Name-String, title: String, description: String, datasets: Dataset-List }


To send request data, create the JSON-format string (encode in UTF8) put it in the request body and send it using PUT or POST.

Response data will be in the response body in JSON format.

Notes:

 * When you update an object, fields that you don't supply will remain as they were before.

 * To delete an 'extra' key-value pair, supply the key with JSON value: ``null``

 * When you read a dataset then some additional information is supplied that cannot current be adjusted throught the CKAN API. This includes info on Dataset Relationship ('relationships'), Group membership ('groups'), ratings ('ratings_average' and 'ratings_count'), full URL of the dataset in CKAN ('ckan_url') and Dataset ID ('id'). This is purely a convenience for clients, and only forms part of the Dataset on GET.

Search API
~~~~~~~~~~

Search resources are available at published locations. They are represented with
a variety of data formats. Each resource location supports a number of methods.

The data formats of the requests and the responses are defined below.

Search Resources
````````````````

Here are the published resources of the Search API.

+---------------------------+--------------------------+
| Search Resource           | Location                 |
+===========================+==========================+
| Dataset Search            | ``/search/dataset``      |
+---------------------------+--------------------------+
| Resource Search           | ``/search/resource``     |
+---------------------------+--------------------------+
| Revision Search           | ``/search/revision``     |
+---------------------------+--------------------------+
| Tag Counts                | ``/tag_counts``          |
+---------------------------+--------------------------+

See below for more information about dataset and revision search parameters.

Search Methods
``````````````

Here are the methods of the Search API.

+-------------------------------+--------+------------------------+--------------------------+
| Resource                      | Method | Request                | Response                 |
+===============================+========+========================+==========================+ 
| Dataset Search                | POST   | Dataset-Search-Params  | Dataset-Search-Response  | 
+-------------------------------+--------+------------------------+--------------------------+
| Resource Search               | POST   | Resource-Search-Params | Resource-Search-Response | 
+-------------------------------+--------+------------------------+--------------------------+
| Revision Search               | POST   | Revision-Search-Params | Revision-List            | 
+-------------------------------+--------+------------------------+--------------------------+
| Tag Counts                    | GET    |                        | Tag-Count-List           | 
+-------------------------------+--------+------------------------+--------------------------+

It is also possible to supply the search parameters in the URL of a GET request, 
for example ``/api/search/dataset?q=geodata&amp;allfields=1``.

Search Formats
``````````````

Here are the data formats for the Search API.

+-------------------------+------------------------------------------------------------+
| Name                    | Format                                                     |
+=========================+============================================================+
| Dataset-Search-Params   | { Param-Key: Param-Value, Param-Key: Param-Value, ... }    |
| Resource-Search-Params  | See below for full details of search parameters across the | 
| Revision-Search-Params  | various domain objects.                                    |
+-------------------------+------------------------------------------------------------+
| Dataset-Search-Response | { count: Count-int, results: [Dataset, Dataset, ... ] }    |
+-------------------------+------------------------------------------------------------+
| Resource-Search-Response| { count: Count-int, results: [Resource, Resource, ... ] }  |
+-------------------------+------------------------------------------------------------+
| Revision-List           | [ Revision-Id, Revision-Id, Revision-Id, ... ]             |
|                         | NB: Ordered with youngest revision first                   |
+-------------------------+------------------------------------------------------------+
| Tag-Count-List          | [ [Name-String, Integer], [Name-String, Integer], ... ]    |
+-------------------------+------------------------------------------------------------+

The ``Dataset`` and ``Revision`` data formats are as defined in `Model Formats`_.

**Dataset Parameters**

+-----------------------+---------------+----------------------------------+----------------------------------+
| Param-Key             | Param-Value   | Examples                         |  Notes                           |
+=======================+===============+==================================+==================================+
| q                     | Search-String || q=geodata                       | Criteria to search the dataset   |
|                       |               || q=government+sweden             | fields for. URL-encoded search   |
|                       |               || q=%22drug%20abuse%22            | text. (You can also concatenate  |
|                       |               |                                  | words with a '+' symbol in a     |
|                       |               |                                  | URL.) Search results must contain|
|                       |               |                                  | all the specified words.         |
+-----------------------+---------------+----------------------------------+----------------------------------+
| qjson                 | JSON encoded  | ['q':'geodata']                  | All search parameters can be     |
|                       | options       |                                  | json-encoded and supplied to this|
|                       |               |                                  | parameter as a more flexible     |
|                       |               |                                  | alternative in GET requests.     |
+-----------------------+---------------+----------------------------------+----------------------------------+
|title,                 | Search-String || title=uk&amp;tags=health+census | Search in a particular a field.  |
|tags, notes, groups,   |               || department=environment          |                                  |
|author, maintainer,    |               |                                  |                                  |
|update_frequency, or   |               |                                  |                                  |
|any 'extra' field name |               |                                  |                                  |
|e.g. department        |               |                                  |                                  |
+-----------------------+---------------+----------------------------------+----------------------------------+
| order_by              | field-name    | order_by=name                    | Specify either rank or the field |
|                       | (default=rank)|                                  | to sort the results by           |
+-----------------------+---------------+----------------------------------+----------------------------------+
| offset, limit         | result-int    | offset=40&amp;limit=20           | Pagination options. Offset is the|
|                       | (defaults:    |                                  | number of the first result and   |
|                       | offset=0,     |                                  | limit is the number of results to|
|                       | limit=20)     |                                  | return.                          |
+-----------------------+---------------+----------------------------------+----------------------------------+
| all_fields            | 0 (default)   | all_fields=1                     | Each matching search result is   |
|                       | or 1          |                                  | given as either a dataset name   |
|                       |               |                                  | (0) or the full dataset record   |
|                       |               |                                  | (1).                             |
+-----------------------+---------------+----------------------------------+----------------------------------+
| filter_by_openness    | 0 (default)   | filter_by_openness=1             | Filters results by ones which are|
|                       | or 1          |                                  | open.                            |
+-----------------------+---------------+----------------------------------+----------------------------------+
|filter_by_downloadable| 0 (default)   | filter_by_downloadable=1          | Filters results by ones which    |
|                       | or 1          |                                  | have at least one resource URL.  |
+-----------------------+---------------+----------------------------------+----------------------------------+

**Resource Parameters**

+-----------------------+---------------+-----------------------------------------+----------------------------------+
| Param-Key             | Param-Value   | Example                                 |  Notes                           |
+=======================+===============+=========================================+==================================+
| url, format,          | Search-String || url=statistics.org                     | Criteria to search the dataset   |
| description           |               || format=xls                             | fields for. URL-encoded search   |
|                       |               || description=Research+Institute         | text. This search string must be |
|                       |               |                                         | found somewhere within the field |
|                       |               |                                         | to match.                        |
|                       |               |                                         | Case insensitive.                |
+-----------------------+---------------+-----------------------------------------+----------------------------------+
| qjson                 | JSON encoded  | ['url':'www.statistics.org']            | All search parameters can be     |
|                       | options       |                                         | json-encoded and supplied to this|
|                       |               |                                         | parameter as a more flexible     |
|                       |               |                                         | alternative in GET requests.     |
+-----------------------+---------------+-----------------------------------------+----------------------------------+
| hash                  | Search-String |hash=b0d7c260-35d4-42ab-9e3d-c1f4db9bc2f0| Searches for an match of the     |
|                       |               |                                         | hash field. An exact match or    |
|                       |               |                                         | match up to the length of the    |
|                       |               |                                         | hash given.                      |
+-----------------------+---------------+-----------------------------------------+----------------------------------+
| all_fields            | 0 (default)   | all_fields=1                            | Each matching search result is   |
|                       | or 1          |                                         | given as either an ID (0) or the |
|                       |               |                                         | full resource record             |
+-----------------------+---------------+-----------------------------------------+----------------------------------+
| offset, limit         | result-int    | offset=40&amp;limit=20                  | Pagination options. Offset is the|
|                       | (defaults:    |                                         | number of the first result and   |
|                       | offset=0,     |                                         | limit is the number of results to|
|                       | limit=20)     |                                         | return.                          |
+-----------------------+---------------+-----------------------------------------+----------------------------------+

**Revision Parameters**

+-----------------------+---------------+-----------------------------------------------------+----------------------------------+
| Param-Key             | Param-Value   | Example                                             |  Notes                           |
+=======================+===============+=====================================================+==================================+ 
| since_time            | Date-Time     | since_time=2010-05-05T19:42:45.854533               | The time can be less precisely   |
|                       |               |                                                     | stated (e.g 2010-05-05).         |
+-----------------------+---------------+-----------------------------------------------------+----------------------------------+
| since_id              | Uuid          | since_id=6c9f32ef-1f93-4b2f-891b-fd01924ebe08       | The stated id will not be        |
|                       |               |                                                     | included in the results.         |
+-----------------------+---------------+-----------------------------------------------------+----------------------------------+

API Keys
~~~~~~~~

You will need to supply an API Key for certain requests to the CKAN API:

* For any action which makes a change to a resource (i.e. all POST methods on register resources, and PUT/POST methods on entity resources).

* If the particular resource's authorization set-up is not open to 
  visitors for the action.

To obtain your API key:

1. Log-in to the particular CKAN website: /user/login

2. The user page has a link to the API Key: /user/apikey

The key should be passed in the API request header:

================= =====
Header            Example value
================= =====
Authorization     ``fde34a3c-b716-4c39-8dc4-881ba115c6d4``
================= =====

If requests that are required to be authorized are not sent with a 
valid Authorization header, for example the user associated with the 
key is not authorized for the operation, or the header is somehow malformed,
then the requested operation will not be carried out and the CKAN API will
respond with status code 403.

For more information about HTTP Authorization header, please refer to section
14.8 of `RFC 2616 <http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.8>`_.


Status Codes
~~~~~~~~~~~~

Standard HTTP status codes are used to signal method outcomes.

===== =====
Code  Name
===== =====
200   OK                 
201   OK and new object created (referred to in the Location header)
301   Moved Permanently  
400   Bad Request     
403   Not Authorized     
404   Not Found          
409   Conflict (e.g. name already exists)
500   Service Error           
===== =====

JSONP formatted responses
~~~~~~~~~~~~~~~~~~~~~~~~~

To cater for scripts from other sites that wish to access the API, the data can be returned in JSONP format, where the JSON data is 'padded' with a function call. The function is named in the 'callback' parameter.

Example normal request::

 GET /api/rest/dataset/pollution_stats
 returns: {"name": "pollution_stats", ... }

but now with the callback parameter::

 GET /api/rest/dataset/pollution_stats?callback=jsoncallback
 returns: jsoncallback({"name": "pollution_stats", ... });

This parameter can apply to all GET requests in the API.


Util API
~~~~~~~~

Some of CKAN's client-side Javascript code makes calls to the CKAN API. For
example, to generate a suggestion for a dataset name when adding a new dataset
the following API call is made:

::

    /api/2/util/dataset/create_slug?title=Dataset+1+Title+Typed+So+Far

The return value is a JSON data structure:

::

    {"valid": true, "name": "dataset_1_title_typed_so_far"}

These are the keys returned:

``valid`` 

    Can be ``True`` or ``False``. It is ``true`` when the title entered can be
    successfully turned into a dataset name and when that dataset name is not
    already being used. It is ``false`` otherwise.

``name``

    The suggested name for the dataset, based on the title

You can also add ``callback=callback`` to have the response returned as JSONP. eg:

This URL:

::

    /api/2/util/dataset/create_slug?title=Dataset+1+Title+Typed+So+Far&callback=callback

Returns:

::

    callback({"valid": true, "name": "dataset_1_title_typed_so_far"});

In some CKAN deployments you may have the API deployed at a different domain
from the main CKAN code. In these circumstances you'll need to add a new option
to the config file to tell the new dataset form where it should make its API
requests to:

::

    ckan.api_url = http://api.example.com/


There is also an autocomplete API for tags which looks like this:

This URL:

::

    /api/2/util/tag/autocomplete?incomplete=ru

Returns:

::

    {"ResultSet": {"Result": [{"Name": "russian"}]}}

Similarly, there is an autocomplete API for the resource format field
which is available at:

::

    /api/2/util/resource/format_autocomplete?incomplete=cs

This returns:

::

    {"ResultSet": {"Result": [{"Format": "csv"}]}}
