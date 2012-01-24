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

Version 3
~~~~~~~~~

This version is in beta. To details of trying it out, see :doc:`apiv3`.



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
| Dataset Relationships Register| POST   | Pkg-Relationship |                   |
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

In general:

* GET to a register resource will *list* the entities of that type.

* GET of an entity resource will *show* the entity's properties.

* POST of entity data to a register resource will *create* the new entity.

* PUT of entity data to an existing entity resource will *update* it.

It is usually clear whether you are trying to create or update, so in these cases, HTTP POST and PUT methods are accepted by CKAN interchangeably.

Model Formats
`````````````

Here are the data formats for the Model API:

+--------------------+------------------------------------------------------------+
| Name               | Format                                                     |
+====================+============================================================+
| Dataset-Ref        | Dataset-Name-String (API v1) OR Dataset-Id-Uuid (API v2)   |
+--------------------+------------------------------------------------------------+
| Dataset-List       | [ Dataset-Ref, Dataset-Ref, Dataset-Ref, ... ]             |
+--------------------+------------------------------------------------------------+
| Dataset            | { id: Uuid, name: Name-String, title: String, version:     | 
|                    | String, url: String, resources: [ Resource, Resource, ...],| 
|                    | author: String, author_email: String, maintainer: String,  |
|                    | maintainer_email: String, license_id: String,              |
|                    | tags: Tag-List, notes: String, extras: { Name-String:      |
|                    | String, ... } }                                            |
|                    | See note below on additional fields upon GET of a dataset. |
+--------------------+------------------------------------------------------------+
| Group-Ref          | Group-Name-String (API v1) OR Group-Id-Uuid (API v2)       |
+--------------------+------------------------------------------------------------+
| Group-List         | [ Group-Ref, Group-Ref, Group-Ref, ... ]                   |
+--------------------+------------------------------------------------------------+
| Group              | { name: Group-Name-String, title: String,                  |
|                    | description: String, datasets: Dataset-List }              |
+--------------------+------------------------------------------------------------+
| Tag-List           | [ Name-String, Name-String, Name-String, ... ]             |
+--------------------+------------------------------------------------------------+
| Tag                | { name: Name-String }                                      |
+--------------------+------------------------------------------------------------+
| Resource           | { url: String, format: String, description: String,        |
|                    | hash: String }                                             |
+--------------------+------------------------------------------------------------+
| Rating             | { dataset: Name-String, rating: int }                      |
+--------------------+------------------------------------------------------------+
| Pkg-Relationships  | [ Pkg-Relationship, Pkg-Relationship, ... ]                |
+--------------------+------------------------------------------------------------+
| Pkg-Relationship   | { subject: Dataset-Name-String,                            |
|                    | object: Dataset-Name-String, type: Relationship-Type,      |
|                    | comment: String }                                          |
+--------------------+------------------------------------------------------------+
| Pkg-Revisions      | [ Pkg-Revision, Pkg-Revision, Pkg-Revision, ... ]          |
+--------------------+------------------------------------------------------------+
| Pkg-Revision       | { id: Uuid, message: String, author: String,               |
|                    | timestamp: Date-Time }                                     |
+--------------------+------------------------------------------------------------+
|Relationship-Type   | One of: 'depends_on', 'dependency_of',                     |
|                    | 'derives_from', 'has_derivation',                          |
|                    | 'child_of', 'parent_of',                                   |
|                    | 'links_to', 'linked_from'.                                 |
+--------------------+------------------------------------------------------------+
| Revision-List      | [ revision_id, revision_id, revision_id, ... ]             |
+--------------------+------------------------------------------------------------+
| Revision           | { id: Uuid, message: String, author: String,               |
|                    | timestamp: Date-Time, datasets: Dataset-List }             |
+--------------------+------------------------------------------------------------+
| License-List       | [ License, License, License, ... ]                         |
+--------------------+------------------------------------------------------------+
| License            | { id: Name-String, title: String, is_okd_compliant:        |
|                    | Boolean, is_osi_compliant: Boolean, tags: Tag-List,        |
|                    | family: String, url: String, maintainer: String,           |
|                    | date_created: Date-Time, status: String }                  |
+--------------------+------------------------------------------------------------+

To send request data, create the JSON-format string (encode in UTF8) put it in the request body and send it using PUT or POST.

Response data will be in the response body in JSON format.

Notes:

 * When you update an object, fields that you don't supply will remain as they were before.

 * To delete an 'extra' key-value pair, supply the key with JSON value: ``null``

 * When you read a dataset, some additional information is supplied that you cannot modify and POST back to the CKAN API. These 'read-only' fields are provided only on the Dataset GET. This is a convenience to clients, to save further requests. This applies to the following fields:
    
===================== ================================
Key                   Description 
===================== ================================
id                    Unique Uuid for the Dataset
revision_id           Latest revision ID for the core Package data (but is not affected by changes to tags, groups, extras, relationships etc)
metadata_created      Date the Dataset (record) was created
metadata_modified     Date the Dataset (record) was last modified
relationships         info on Dataset Relationships
ratings_average         
ratings_count            
ckan_url              full URL of the Dataset
download_url (API v1) URL of the first Resource
isopen                boolean indication of whether dataset is open according to Open Knowledge Definition, based on other fields
notes_rendered        HTML rendered version of the Notes field (which may contain Markdown)
===================== ================================
   


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
|                       |               || q=tags:"river pollution"        | words with a '+' symbol in a     |
|                       |               |                                  | URL.) Search results must contain|
|                       |               |                                  | all the specified words.  You    |
|                       |               |                                  | can also search within specific  |
|                       |               |                                  | fields.                          |
+-----------------------+---------------+----------------------------------+----------------------------------+
| qjson                 | JSON encoded  | ['q':'geodata']                  | All search parameters can be     |
|                       | options       |                                  | json-encoded and supplied to this|
|                       |               |                                  | parameter as a more flexible     |
|                       |               |                                  | alternative in GET requests.     |
+-----------------------+---------------+----------------------------------+----------------------------------+
|title,                 | Search-String || title=uk&amp;tags=health        | Search in a particular a field.  |
|tags, notes, groups,   |               || department=environment          |                                  |
|author, maintainer,    |               || tags=health&tags=pollution      |                                  |
|update_frequency, or   |               || tags=river%20pollution          |                                  |
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

.. Note::

 filter_by_openness and filter_by_downloadable were dropped from CKAN version 1.5 onwards.


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

.. Note::

   Powerful searching from the command-line can be achieved with curl and the qjson parameter. In this case you need to remember to escapt the curly braces and use url encoding (e.g. spaces become ``%20``). For example::

     curl 'http://thedatahub.org/api/search/dataset?qjson=\{"author":"The%20Stationery%20Office%20Limited"\}'


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

2. The user page shows the API Key: /user/me

The key should be passed in the API request header ''Authorization'' (or an alternative may be provided such as ''X-CKAN-API-KEY''). For example::

  curl http://thedatahub.org/api/rest/package -d '{"name": "test"}' -H 'Authorization: fde34a3c-b716-4c39-8dc4-881ba115c6d4'

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

These utilities don't involve the CKAN database, but can be useful to scripts and code on the Web front-end (i.e. AJAX calls). 

The response format is JSON. Javascript calls may want to use the JSONP formatting.

.. Note::

  Some CKAN deployments have the API deployed at a different domain to the main CKAN website. To make sure that the AJAX calls in the Web UI work, you'll need to configue the ckan.api_url. e.g.::

    ckan.api_url = http://api.example.com/


dataset autocomplete
````````````````````

There an autocomplete API for package names which matches on name or title.

This URL:

::

    /api/2/util/dataset/autocomplete?incomplete=a%20novel

Returns:

::

    {"ResultSet": {"Result": [{"match_field": "title", "match_displayed": "A Novel By Tolstoy (annakarenina)", "name": "annakarenina", "title": "A Novel By Tolstoy"}]}}


tag autocomplete
````````````````

There is also an autocomplete API for tags which looks like this:

This URL:

::

    /api/2/util/tag/autocomplete?incomplete=ru

Returns:

::

    {"ResultSet": {"Result": [{"Name": "russian"}]}}

resource format autocomplete
````````````````````````````

Similarly, there is an autocomplete API for the resource format field
which is available at:

::

    /api/2/util/resource/format_autocomplete?incomplete=cs

This returns:

::

    {"ResultSet": {"Result": [{"Format": "csv"}]}}

markdown
````````

Takes a raw markdown string and returns a corresponding chunk of HTML. CKAN uses the basic Markdown format with some modifications (for security) and useful additions (e.g. auto links to datasets etc. e.g. ``dataset:river-quality``).

Example::

    /api/util/markdown?q=<http://ibm.com/>

Returns::

    "<p><a href="http://ibm.com/" target="_blank" rel="nofollow">http://ibm.com/</a>\n</p>"

is slug valid
`````````````

Checks a name is valid for a new dataset (package) or group, with respect to it being used already.

Example::

    /api/2/util/is_slug_valid?slug=river-quality&type=package

Response::

    {"valid": true}

munge package name
``````````````````

For taking an readable identifier and munging it to ensure it is a valid dataset id. Symbols and whitespeace are converted into dashes. Example::

    /api/util/dataset/munge_name?name=police%20spending%20figures%202009

Returns::

    "police-spending-figures-2009"

munge title to package name
```````````````````````````

For taking a title of a package and munging it to a readable and valid dataset id. Symbols and whitespeace are converted into dashes, with multiple dashes collapsed. Ensures that long titles with a year at the end preserves the year should it need to be shortened. Example::

    /api/util/dataset/munge_title_to_name?title=police:%20spending%20figures%202009

Returns::

    "police-spending-figures-2009"


munge tag
`````````

For taking a readable word/phrase and munging it to a valid tag (name). Symbols and whitespeace are converted into dashes. Example::

    /api/util/tag/munge?tag=water%20quality

Returns::

    "water-quality"

Action API
~~~~~~~~~~

See: :doc:`apiv3`
