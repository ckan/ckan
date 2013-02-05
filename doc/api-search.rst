==============
The Search API
==============

Search resources are available at published locations. They are represented with
a variety of data formats. Each resource location supports a number of methods.

The data formats of the requests and the responses are defined below.

Search Resources
----------------

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
--------------

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
--------------

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

**Dataset Parameters**

These parameters are all the standard SOLR syntax (in contrast to the syntax used in CKAN API versions 1 and 2). Here is a summary of the main features:

+-----------------------+---------------+----------------------------------+----------------------------------+
| Param-Key             | Param-Value   | Examples                         |  Notes                           |
+=======================+===============+==================================+==================================+
| q                     | Search-String || q=geodata                       | Criteria to search the dataset   |
|                       |               || q=government%20sweden           | fields for. URL-encoded search   |
|                       |               || q=%22drug%20abuse%22            | text. Search results must contain|
|                       |               || q=title:census                  | all the specified words. Use     |
|                       |               || q=tags:maps&tags:country-uk     | colon to specify which field to  |
|                       |               |                                  | search in. (Extra fields are not |
|                       |               |                                  | currently supported.)            |
+-----------------------+---------------+----------------------------------+----------------------------------+
| qjson                 | JSON encoded  | ['q':'geodata']                  | All search parameters can be     |
|                       | options       |                                  | json-encoded and supplied to this|
|                       |               |                                  | parameter as a more flexible     |
|                       |               |                                  | alternative in GET requests.     |
+-----------------------+---------------+----------------------------------+----------------------------------+
| fl                    | list of fields|| fl=name                         | Which fields to return. * is all.|
|                       |               || fl=name,title                   |                                  |
|                       |               || fl=*                            |                                  |
+-----------------------+---------------+----------------------------------+----------------------------------+
| sort                  | field name,   || sort=name asc                   | Changes the sort order according |
|                       | asc / dec     || sort=metadata_modified asc      | to the field and direction given.|
|                       |               |                                  | default: score desc, name asc    |
+-----------------------+---------------+----------------------------------+----------------------------------+
| start, rows           | result-int    | start=40&amp;rows=20             | Pagination options. Start is the |
|                       | (defaults:    |                                  | number of the first result and   |
|                       | start=0,      |                                  | rows is the number of results to |
|                       | rows=20)      |                                  | return.                          |
+-----------------------+---------------+----------------------------------+----------------------------------+
| all_fields            | 0 (default)   | all_fields=1                     | Each matching search result is   |
|                       | or 1          |                                  | given as either a dataset name   |
|                       |               |                                  | (0) or the full dataset record   |
|                       |               |                                  | (1).                             |
+-----------------------+---------------+----------------------------------+----------------------------------+

.. Note: filter_by_openness and filter_by_downloadable were dropped from CKAN version 1.5 onwards.


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


Status Codes
~~~~~~~~~~~~

The Search API returns standard HTTP status codes to signal method outcomes:

===== =====
Code  Name
===== =====
200   OK
201   OK and new object created (referred to in the Location header)
301   Moved Permanently (redirect)
400   Bad Request
403   Not Authorized - have you forgotton to specify your API Key?
404   Not Found
409   Conflict - error during processing of the request
500   Service Error - unhandled error - the system administrator has been notified
===== =====
