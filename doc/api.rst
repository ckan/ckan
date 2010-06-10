============
The CKAN API
============


A CKAN server's data catalog is not only available in a web browser, but also
via its Application Programming Interface (API). The API can be used to view
and change the catalog.

This document describes the CKAN API, so that anyone can create software
applications that use CKAN API services.


Code Modules for Client Applications
====================================

There are also some code modules (Python, PHP, Drupal, Perl etc.) that provide 
convenient wrappers around much of the CKAN API. For full details of these, 
please consult: http://wiki.okfn.org/ckan/related


Example of Usage
================

You're using ckan.net and want a list of all the packages. If you GET
``http://ckan.net/api/rest/package`` then it will return the list of the package
names in JSON format::

["2000-us-census-rdf", "32000-naples-florida-businesses-kml", "aaoe-87", "acawiki", "adb-sdbs", "addgene", "advances-in-dental-research", ... ]

There are several ways you might access this URL:

* simply put this URL into your web browser and save the resulting text file

* you could use a command-line program such as curl or wget

* you could write a program that uses an http library

* use the Python library 'CKAN Client'

* use 'Datapkg', for getting datasets listed in CKAN in a similar way to getting software packages

You could search for packages to do with 'open street map' like this: ``http://ckan.net/api/search/package?q=open+street+map`` returning::

{"count": 4, "results": ["uk-naptan-osm", "osm-uk", "osm", "naptan"]}

You can see the full record for the osm package in JSON format with this: ``http://ckan.net/api/rest/package/osm`` which returns::

{"name": "osm", "resources": [{"url": "http://wiki.openstreetmap.org/index.php/Planet.osm", "description": "All data", "format": ""}], "tags": ["navigation", "openstreetmap", "map", "geo", "geodata", "xml", "publicdomain", "osm"] ... }

You might add a tag by POSTing to ``http://ckan.net/api/rest/package/osm`` this::

"tags": ["navigation", "openstreetmap", "map", "geo", "geodata", "xml", "publicdomain", "osm", "my-new-tag"]

So that the system knows who is making this change, you need to send your API key in the headers - see `CKAN API Keys`_.


Overview
========

The CKAN API is separated into two parts:

* the Model API; and
* the Search API.

The CKAN API follows the RESTful (Representational State Transfer) style.
Published resources are separated both from the methods supported by the
resources, and from the data formats and status codes used by the methods.

At the same time, clients can proceed by following related resources
identified in server responses. For example, after successfully POSTing data
to a model register, the location of the newly created entity is indicated in
the method response's 'Location' header.


API Versions
============

The CKAN API is versioned, so that backwards incompatible changes can be
introduced without removing existing support. The version number is inserted
after the '/api' part of the path.

``http://ckan.net/api/API-VERSION/rest/package``

For example versions 1 and 2 of the CKAN API are located here:

``http://ckan.net/api/1/rest/package``
``http://ckan.net/api/2/rest/package``

Clients that don't supply the version number access version 1 by default.


CKAN Model API
==============

Model resources are available at published locations. They are represented with
a variety of data formats. Each resource location supports a number of methods.

The data formats of the requests and the responses are defined below.


Model API Resources
-------------------

Here are the resources of the Model API.

+--------------------------------+-------------------------------------------------------------------+
| Resource                       | Location                                                          |
+================================+===================================================================+
| Package Register               | ``/api/rest/package``                                             |
+--------------------------------+-------------------------------------------------------------------+
| Package Entity                 | ``/api/rest/package/PACKAGE-REF``                                 |
+--------------------------------+-------------------------------------------------------------------+
| Group Register                 | ``/api/rest/group``                                               |
+--------------------------------+-------------------------------------------------------------------+
| Group Entity                   | ``/api/rest/group/GROUP-NAME``                                    |
+--------------------------------+-------------------------------------------------------------------+
| Tag Register                   | ``/api/rest/tag``                                                 |
+--------------------------------+-------------------------------------------------------------------+
| Tag Entity                     | ``/api/rest/tag/TAG-NAME``                                        |
+--------------------------------+-------------------------------------------------------------------+
| Rating Register                | ``/api/rest/rating``                                              |
+--------------------------------+-------------------------------------------------------------------+
| Rating Entity                  | ``/api/rest/rating/PACKAGE-REF``                                  |
+--------------------------------+-------------------------------------------------------------------+
| Package Relationships Register | ``/api/rest/package/PACKAGE-REF/relationships``                   |
+--------------------------------+-------------------------------------------------------------------+
| Package Relationships Register | ``/api/rest/package/PACKAGE-REF/relationships/PACKAGE-REF``       |
+--------------------------------+-------------------------------------------------------------------+
| Package Relationship Entity    | ``/api/rest/package/PACKAGE-REF/RELATIONSHIP-TYPE/PACKAGE-REF``   |
+--------------------------------+-------------------------------------------------------------------+
| Revision Register              | ``/api/rest/revision``                                            |
+--------------------------------+-------------------------------------------------------------------+
| Revision Entity                | ``/api/rest/revision/REVISION-ID``                                |
+--------------------------------+-------------------------------------------------------------------+
| License List                   | ``/api/rest/licenses``                                            |
+--------------------------------+-------------------------------------------------------------------+

Possible values for PACKAGE-REF are the package id, or the current package name.

Possible values for RELATIONSHIP-TYPE are described in the Relationship-Type data format.


Model API Methods
-----------------

Here are the methods of the Model API.

+-------------------------------+--------+------------------+-------------------+
| Resource                      | Method | Request          | Response          |
+===============================+========+==================+===================+ 
| Package Register              | GET    |                  | Package-List      | 
+-------------------------------+--------+------------------+-------------------+
| Package Register              | POST   | Package          |                   | 
+-------------------------------+--------+------------------+-------------------+
| Package Entity                | GET    |                  | Package           | 
+-------------------------------+--------+------------------+-------------------+
| Package Entity                | PUT    | Package          |                   | 
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
| Tag Entity                    | GET    |                  | Package-List      | 
+-------------------------------+--------+------------------+-------------------+
| Rating Register               | POST   | Rating           |                   | 
+-------------------------------+--------+------------------+-------------------+
| Rating Entity                 | GET    |                  | Rating            | 
+-------------------------------+--------+------------------+-------------------+
| Package Relationships Register| GET    |                  | Pkg-Relationships | 
+-------------------------------+--------+------------------+-------------------+
| Package Relationship Entity   | GET    |                  | Pkg-Relationship  |
+-------------------------------+--------+------------------+-------------------+
| Package Relationship Entity   | PUT    | Pkg-Relationship |                   | 
+-------------------------------+--------+------------------+-------------------+
| Revision Entity               | GET    |                  | Revision          | 
+-------------------------------+--------+------------------+-------------------+
| License List                  | GET    |                  | License-List      | 
+-------------------------------+--------+------------------+-------------------+

* The location of new entity resources will be indicated in the 'Location' header containing the resource location of the new entity.

* PUT operations may instead use the HTTP POST method with the same.

* POSTing data to a register resource will create a new entity, whilst PUT/POSTing data to an entity resource will update an existing entity.


Model API Data Formats
----------------------

Here are the data formats for the Model API.

Todo: Fork API documentation.

+-----------------+------------------------------------------------------------+
| Name            | Format                                                     |
+=================+============================================================+
| Package-List    | [ Name-String, Name-String, Name-String, ... ]             |
| (API v1 only)   |                                                            |
+-----------------+------------------------------------------------------------+
| Package-List    | [ Id-String, Id-String, Id-String, ... ]                   |
| (API v2 only)   |                                                            |
+-----------------+------------------------------------------------------------+
| Package         | { name: Name-String, title: String, version: String,       |
|                 | url: String, resources: [ Resource, Resource, ...],        |
|                 | author: String, author_email: String,                      |
|                 | maintainer: String, maintainer_email: String,              |
|                 | license_id: String, tags: Tag-List, notes: String,         |
|                 | extras: { Name-String: String, ... } }                     |
|                 | See note below on additional fields upon GET of a package. |
+-----------------+------------------------------------------------------------+
| Group-List      | [ Name-String, Name-String, Name-String, ... ]             | 
+-----------------+------------------------------------------------------------+
| Group           | { name: Name-String, title: String, description: String,   | 
|                 | packages: Package-List }                                   |
+-----------------+------------------------------------------------------------+
| Tag-List        | [ Name-String, Name-String, Name-String, ... ]             |
+-----------------+------------------------------------------------------------+
| Tag             | { name: Name-String }                                      |
+-----------------+------------------------------------------------------------+
| Resource        | { url: String, format: String, description: String,        |
|                 | hash: String }                                             |
+-----------------+------------------------------------------------------------+
| Rating          | { package: Name-String, rating: int }                      |
+-----------------+------------------------------------------------------------+
|Pkg-Relationships| [ Pkg-Relationship, Pkg-Relationship, ... ]                |
+-----------------+------------------------------------------------------------+
| Pkg-Relationship| { subject: Package-Name-String,                            |
|                 | object: Package-Name-String, type: Relationship-Type,      |
|                 | comment: String }                                          |
+-----------------+------------------------------------------------------------+
|Relationship-Type| One of: 'depends_on', 'dependency_of',                     |
|                 | 'derives_from', 'has_derivation',                          |
|                 | 'child_of', 'parent_of'.                                   |
+-----------------+------------------------------------------------------------+
| Revision        | { id: Uuid, message: String, author: String,               |
|                 | timestamp: Date-Time, packages: Package-List }             |
+-----------------+------------------------------------------------------------+
| License-List    | [ License, License, License, ... ]                         |
+-----------------+------------------------------------------------------------+
| License         | { id: Name-String, title: String, is_okd_compliant:        |
|                 | Boolean, is_osi_compliant: Boolean, tags: Tag-List,        |
|                 | family: String, url: String, maintainer: String,           |
|                 | date_created: Date-Time, status: String }                  |
+-----------------+------------------------------------------------------------+
| Name-String     | An alphanumeric string.                                    |
+-----------------+------------------------------------------------------------+

To send request data, create a simple data structure, then convert it to a JSON string, then percent-encode the JSON string, then send it as the request body.

Response data will be in the response body.

Notes:

 * When you update an object, fields that you don't supply will remain as they were before.

 * To delete an 'extra' key-value pair, supply the key with a None value.

 * When you read a package then some additional information is supplied that cannot current be adjusted throught the CKAN API. This includes info on Package Relationship ('relationships'), Group membership ('groups'), ratings ('ratings_average' and 'ratings_count') and Package ID ('id'). This is purely a convenience for clients, and only forms part of the Package on GET.


CKAN Search API
===============

Search resources are available at published locations. They are represented with
a variety of data formats. Each resource location supports a number of methods.

The data formats of the requests and the responses are defined below.


Search API Resources
--------------------

Here are the published resources of the CKAN Search API.

+---------------------------+--------------------------+
| Resource                  | Location                 |
+===========================+==========================+
| Package Search            | ``/api/search/package``  |
+---------------------------+--------------------------+
| Revision Search           | ``/api/search/revision`` |
+---------------------------+--------------------------+
| Tag Counts                | ``/api/tag_counts``      |
+---------------------------+--------------------------+

See below for more information about package and revision search parameters.


Search API Methods
------------------

Here are the methods of the CKAN Search API.

+-------------------------------+--------+------------------------+-------------------+
| Resource                      | Method | Request                | Response          |
+===============================+========+========================+===================+ 
| Package Search                | POST   | Package-Search-Params  | Search-Response   | 
+-------------------------------+--------+------------------------+-------------------+
| Revision Search               | POST   | Revision-Search-Params | Revision-List     | 
+-------------------------------+--------+------------------------+-------------------+
| Tag Counts                    | GET    |                        | Tag-Count-List    | 
+-------------------------------+--------+------------------------+-------------------+

It is also possible to supply the search parameters in the URL of a GET request, 
for example ``/api/search/package?q=geodata&amp;allfields=1``.


Search API Data Formats
-----------------------

Here are the data formats for the Search API.

+-----------------------+------------------------------------------------------------+
| Name                  | Format                                                     |
+=======================+============================================================+
| Package-Search-Params | { Param-Key: Param-Value, Param-Key: Param-Value, ... }    |
| Revision-Search-Params| See below for full details of search parameters across the | 
|                       | various domain objects.                                    |
+-----------------------+------------------------------------------------------------+
| Search-Response       | { count: Count-int, results: [Package, Package, ... ] }    |
+-----------------------+------------------------------------------------------------+
| Revision-List         | [ Revision-Id, Revision-Id, Revision-Id, ... ]             |
|                       | NB: Ordered with youngest revision first                   |
+-----------------------+------------------------------------------------------------+
| Tag-Count-List        | [ [Name-String, Integer], [Name-String, Integer], ... ]    |
+-----------------------+------------------------------------------------------------+

The ``Package`` and ``Revision`` data formats are as defined in `Model API Data Formats`_.


Package Search Parameters
~~~~~~~~~~~~~~~~~~~~~~~~~

+-----------------------+---------------+----------------------------------+----------------------------------+
| Param-Key             | Param-Value   | Example                          |  Notes                           |
+=======================+===============+==================================+==================================+
| q                     | Search-String || q=geodata                       | Criteria to search the package   |
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
|title,                 | Search-String | title=uk&amp;tags=health+census  | Search a particular a field. Note|
|tags, notes, groups,   |               |                                  | that the latter fields mentioned |
|author, maintainer,    |               |                                  | here are in the 'extra' fields.  |
|update_frequency,      |               |                                  |                                  |
|geographic_granularity,|               |                                  |                                  |
|geographic_coverage,   |               |                                  |                                  |
|temporal_granularity,  |               |                                  |                                  |
|temporal_coverage,     |               |                                  |                                  |
|national_statistic,    |               |                                  |                                  |
|categories,            |               |                                  |                                  |
|precision,             |               |                                  |                                  |
|department, agency,    |               |                                  |                                  |
|external_reference     |               |                                  |                                  |
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
|                       | or 1          |                                  | given as either a package name   |
|                       |               |                                  | (0) or the full package record   |
|                       |               |                                  | (1).                             |
+-----------------------+---------------+----------------------------------+----------------------------------+
| filter_by_openness    | 0 (default)   | filter_by_openness=1             | Filters results by ones which are|
|                       | or 1          |                                  | open.                            |
+-----------------------+---------------+----------------------------------+----------------------------------+
|filter_by_downloadbable| 0 (default)   | filter_by_downloadable=1         | Filters results by ones which    |
|                       | or 1          |                                  | have at least one resource URL.  |
+-----------------------+---------------+----------------------------------+----------------------------------+


Revision Search Parameters
~~~~~~~~~~~~~~~~~~~~~~~~~~

+-----------------------+---------------+-----------------------------------------------------+----------------------------------+
| Param-Key             | Param-Value   | Example                                             |  Notes                           |
+=======================+===============+=====================================================+==================================+ 
| since_time            | Date-Time     | since_time=2010-05-05T19:42:45.854533               | The time can be less precisely   |
|                       |               |                                                     | stated (e.g 2010-05-05).         |
+-----------------------+---------------+-----------------------------------------------------+----------------------------------+
| since_id              | Uuid          | since_id=6c9f32ef-1f93-4b2f-891b-fd01924ebe08       | The stated id will not be        |
|                       |               |                                                     | included in the results.         |
+-----------------------+---------------+-----------------------------------------------------+----------------------------------+


CKAN API Status Codes
=====================

Standard HTTP status codes are used to signal method outcomes.

===== =====
Code  Name
===== =====
200   OK                 
301   Moved Permanently  
400   Bad Request     
403   Not Authorized     
404   Not Found          
409   Conflict (e.g. name already exists)
500   Service Error           
===== =====


CKAN API Keys
=============

You will need to supply an API Key for certain requests to the CKAN API:

* For any action which makes a change to a resource (i.e. all POST methods on register resources, and PUT/POST methods on entity resources).

* If the particular resource's authorization set-up is not open to 
  visitors for the action.

To obtain your API key:

1. Log-in to the particular CKAN website: /user/login

2. The user page has a link to the API Key: /user/apikey

The key should be passed in the API request header:

====================== =====
Header                 Example value
====================== =====
HTTP_AUTHORIZATION     fde34a3c-b716-4c39-8dc4-881ba115c6d4
====================== =====

If requests that are required to be authorized are not sent with a currently 
valid Authorization header, or the user associated with the key is not 
authorized for the operation, then the requested operation will not be carried
out and the CKAN API will respond with status code 403.


