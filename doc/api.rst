=========================
CKAN API (including REST)
=========================

Introduction
============

A CKAN server's data catalog is not only available in a web browser, but also via its 
Application Programming Interface (API). The API can be used to view and change
the CKAN data.

The API has two basic sections:

* a RESTful (Representational State Transfer) style interface for accessing 
  CKAN database objects

* a Search API

This document specifies the API so that anyone can create software applications
to use the CKAN service. The specification describes the RESTful API in terms
of which resources are available, what their locations are, what methods each
resource supports, and what the responses might be. It also species the usage
and responses to the Search API.


Example
=======

You're using ckan.net and want a list of all the packages. If you GET
http://ckan.net/api/rest/package then it will return the list of the package
names in JSON format::

["2000-us-census-rdf", "32000-naples-florida-businesses-kml", "aaoe-87", "acawiki", "adb-sdbs", "addgene", "advances-in-dental-research", ... ]

There are several ways you might access this URL:

* simply put this URL into your web browser and save the resulting text file

* you could use a command-line program such as curl or wget

* you could write a program that uses an http library

* use the Python library 'CKAN Client'

* use 'Datapkg', for getting datasets listed in CKAN in a similar way to getting software packages

You could search for packages to do with 'open street map' like this: http://ckan.net/api/search/package?q=open+street+map returning::

{"count": 4, "results": ["uk-naptan-osm", "osm-uk", "osm", "naptan"]}

You can see the full record for the osm package in JSON format with this: http://ckan.net/api/rest/package/osm which returns::

{"name": "osm", "resources": [{"url": "http://wiki.openstreetmap.org/index.php/Planet.osm", "description": "All data", "format": ""}], "tags": ["navigation", "openstreetmap", "map", "geo", "geodata", "xml", "publicdomain", "osm"] ... }

You might add a tag by POSTing to http://ckan.net/api/rest/package/osm this::

"tags": ["navigation", "openstreetmap", "map", "geo", "geodata", "xml", "publicdomain", "osm", "my-new-tag"]

So that the system knows who is making this change, you need to send your API key in the headers.


API Locations
=============

A REST interface presents resources at published locations. Here are the names
locations of the CKAN REST API resources:

+--------------------------------+---------------------------------------------------------------+
| Resource Name                  | Location                                                      |
+================================+===============================================================+
| Package Register               | /api/rest/package                                             |
+--------------------------------+---------------------------------------------------------------+
| Package Entity                 | /api/rest/package/PACKAGE-NAME                                |
+--------------------------------+---------------------------------------------------------------+
| Group Register                 | /api/rest/group                                               |
+--------------------------------+---------------------------------------------------------------+
| Group Entity                   | /api/rest/group/GROUP-NAME                                    |
+--------------------------------+---------------------------------------------------------------+
| Tag Register                   | /api/rest/tag                                                 |
+--------------------------------+---------------------------------------------------------------+
| Tag Entity                     | /api/rest/tag/TAG-NAME                                        |
+--------------------------------+---------------------------------------------------------------+
| Rating Registry                | /api/rest/rating                                              |
+--------------------------------+---------------------------------------------------------------+
| Rating Entity                  | /api/rest/rating/PACKAGE-NAME                                 |
+--------------------------------+---------------------------------------------------------------+
| Package Relationships Register | /api/rest/package/PACKAGE-NAME/relationships                  |
+--------------------------------+---------------------------------------------------------------+
| Package Relationships Register | /api/rest/package/PACKAGE-NAME/relationships/PACKAGE-NAME     |
+--------------------------------+---------------------------------------------------------------+
| Package Relationship Entity    | /api/rest/package/PACKAGE-NAME/RELATIONSHIP-NAME/PACKAGE-NAME |
+--------------------------------+---------------------------------------------------------------+
| Revision Entity                | /api/rest/revision/REVISION-ID                                |
+--------------------------------+---------------------------------------------------------------+
| License List                   | /api/rest/licenses                                            |
+--------------------------------+---------------------------------------------------------------+

Here are the non-REST API locations:

+-------------------+-----------------------+
| API functions     | Location              |
+===================+=======================+
| Package Search    | /api/search/package   |
+-------------------+-----------------------+
| Tag Counts        | /api/tag_counts       |
+-------------------+-----------------------+
| Revision Search   | /api/search/revision  |
+-------------------+-----------------------+

See below for more information about package and revision search parameters.


Methods and data formats
========================

Each resource location supports a number of methods, which may send or receive
a piece of data. Standard http status codes are used to signal the outcome of
the operation.

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
| Tag Entity                    | GET    | Tag              | Package-List      | 
+-------------------------------+--------+------------------+-------------------+
| Rating Entity                 | GET    |                  | Rating            | 
+-------------------------------+--------+------------------+-------------------+
| Rating Register               | POST   | Rating           |                   | 
+-------------------------------+--------+------------------+-------------------+
| Package Relationship Entity   | GET    |                  | Pkg-Relationship  |
+-------------------------------+--------+------------------+-------------------+
| Package Relationship Entity   | POST   | Pkg-Relationship |                   | 
+-------------------------------+--------+------------------+-------------------+
| Package Relationship Entity   | PUT    | Pkg-Relationship |                   | 
+-------------------------------+--------+------------------+-------------------+
| Package Relationship Register | GET    | Rating           | Pkg-Relationships | 
+-------------------------------+--------+------------------+-------------------+
| Search                        | GET    |                  | Search-Response   | 
+-------------------------------+--------+------------------+-------------------+
| Search                        | POST   | Query-String     | Search-Response   | 
+-------------------------------+--------+------------------+-------------------+
| Tag Counts                    | GET    |                  | Tag-Count-List    | 
+-------------------------------+--------+------------------+-------------------+
| Revision Entity               | GET    |                  | Revision          | 
+-------------------------------+--------+------------------+-------------------+
| License List                  | GET    |                  | License-List      | 
+-------------------------------+--------+------------------+-------------------+

Notes:

* 'PUT' operations may instead use the HTTP POST method.

* To search, there are two ways to provide parameters - you can use either or
  both ways in each search request. The first method is to provide them as
  parameters in the URL, (e.g. /api/rest/search?q=geodata&amp;allfields=1 ). The
  second way is to encode the parameters as a JSON dictionary and supply them
  in the POST request.


Data Formats
============

+-----------------+------------------------------------------------------------+
| Name            | Format                                                     |
+=================+============================================================+
| Package-List    | [ Name-String, Name-String, Name-String, ... ]             |
+-----------------+------------------------------------------------------------+
| Package         | { name: Name-String, title: String, version: String,       |
|                 | url: String, resources: [ Resource-Dict, Resource-Dict,    |
|                 | ... ], author: String, author_email: String,               |
|                 | maintainer: String, maintainer_email: String,              |
|                 | license_id: Stringw, tags: Tag-List, notes: String,         |
|                 | extras: { Name-String: Value-String, ... } }               |
+-----------------+------------------------------------------------------------+
| Group-List      | [ Name-String, Name-String, Name-String, ... ]             | 
+-----------------+------------------------------------------------------------+
| Group           | { name: Name-String, title: String, description: String,   | 
|                 | packages: Group-List }                                     |
+-----------------+------------------------------------------------------------+
| Tag-List        | [ Name-String, Name-String, Name-String, ... ]             |
+-----------------+------------------------------------------------------------+
| Tag             | { name: Name-String }                                      |
+-----------------+------------------------------------------------------------+
| Name-String     | An alphanumeric string.                                    |
+-----------------+------------------------------------------------------------+
| Resource-Dict   | { url: String, format: String, description: String,        |
|                 | hash: String }                                             |
+-----------------+------------------------------------------------------------+
| Rating          | { package: Name-String, rating: int }                      |
+-----------------+------------------------------------------------------------+
| Ratings         | { ratings_average: float, ratings_count: int }             |
+-----------------+------------------------------------------------------------+
| Query-String    | [ q: String ]                                              |
+-----------------+------------------------------------------------------------+
| Search-Response | { count: Count-int, results: [Package-Name-String,         |
|                 | Package-Name-String, ... ] }                               |
|                 | **or**                                                     |
|                 | { count: Count-int,                                        |
|                 | results: [{ name:Name-String, title: String ... },         |
|                 | { name:Name-String, title: String ... }, ... ]}            |
+-----------------+------------------------------------------------------------+
| Tag-Count-List  | [ [tag-name, tag-count], [tag-name, tag-count], ... ]      |
+-----------------+------------------------------------------------------------+
| Pkg-Relationship| {'comment':String}                                         |
+-----------------+------------------------------------------------------------+
|RELATIONSHIP-NAME| One of: 'child_of', 'parent_of', 'depends_on',             |
|                 | 'dependency_of', 'derives_from', 'has_derivation'          |
+-----------------+------------------------------------------------------------+
| Pkg-Relationship| {'comment':String}                                         |
+-----------------+------------------------------------------------------------+
| Revision-List   | [ Uuid, Uuid, Uuid, ... ]                                  |
+-----------------+------------------------------------------------------------+
| Revision        | { id: Uuid, message: String, author: String,               |
|                 | timestamp: Date-Time }                                      |
+-----------------+------------------------------------------------------------+
| License-List    | [ License, License, License, ... ]                         |
+-----------------+------------------------------------------------------------+
| License         | [ id: Name-String, title: String, is_okd_compliant:        |
|                 | Boolean, is_osi_compliant: Boolean, tags: Tag-List,        |
|                 | family: String, url: String, maintainer: String,           |
|                 | date_created: Date-Time, status: String ]                   |
+-----------------+------------------------------------------------------------+

To send request data, create a simple data structure, then convert it to a JSON string, then percent-encode the JSON string, then send it as the request body.

Response data will be in the response body.

Notes:

 * When you update an object, fields that you don't supply will remain as they were before.

 * To delete an 'extra' key-value pair, supply the key with a None value.

 * When you read a package then some additional information is supplied that cannot be edited in the REST style. This includes info on Package Relationship. This is a convenience.


API Keys
========

You will need to supply an API Key for certain requests to the REST API:

* For any action which makes a change to a resource (i.e. all non-GET methods)

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
out and the CKAN REST API will respond with status code 403.


Package Search Parameters
=========================

+-----------------------+---------------+----------------------------------+----------------------------------+
| Key                   |    Value      | Example                          |  Notes                           |
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
|                       |               |                                  | URL parameter as a more flexible | 
|                       |               |                                  | alternative.                     |
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
==========================

+-----------------------+---------------+----------------------------------+----------------------------------+
| Key                   |    Value      | Example                          |  Notes                           |
+=======================+===============+==================================+==================================+ 
| since_time            | Date-Time     |                                  |                                  |
+-----------------------+---------------+----------------------------------+----------------------------------+
| since_revision        | Uuid          |                                  |                                  |
+-----------------------+---------------+----------------------------------+----------------------------------+


Status Codes
============

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
