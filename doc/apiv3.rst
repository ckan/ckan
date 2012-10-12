=======================================
Model, Search and Action API: Version 3
=======================================

API Versions
~~~~~~~~~~~~

To use a particular version of the API, include the version number in the base of the URL:
 * ``http://ckan.net/api/1`` (version 1)
 * ``http://ckan.net/api/2`` (version 2)
 * ``http://ckan.net/api/3`` (version 3)
e.g. Searching using API version 2::
 http://ckan.net/api/2/search/dataset?q=spending

If you don't specify the version number then you will default to version 1 of the Model, Search and Util APIs and version 3 of the Action API.
 * ``http://ckan.net/api/rest`` (version 1)
 * ``http://ckan.net/api/search`` (version 1)
 * ``http://ckan.net/api/util`` (version 1)
 * ``http://ckan.net/api/action`` (version 3)

.. _action-api:

Action API
~~~~~~~~~~

.. warning:: The Action API is in beta in this release. Please feed back comments and problems. There is a known issue that incorrect parameters cause unhelpful errors with status 500.

Overview
--------

The Action API is a powerful RPC-style way of accessing CKAN data. Its intention is to have access to all the core logic in ckan. It calls exactly the same functions that are used internally which all the other CKAN interfaces (Web interface / Model API) go through. Therefore it provides the full gamut of read and write operations, with all possible parameters.

A client supplies parameters to the Action API via a JSON dictionary of a POST request, and returns results, help information and any error diagnostics in a JSON dictionary too. This is a departure from the CKAN API versions 1 and 2, which being RESTful required all the request parameters to be part of the URL.

In addition to the above, any of the actions defined in
`ckan/logic/action/get.py` can be accessed with a GET request to the same URI
endpoint.  See below for examples.

URL
===

The basic URL for the Action API is::

 /api/action/{logic_action}

Examples::

 /api/action/package_list
 /api/action/package_show
 /api/action/user_create

Parameters
==========

All actions accept POST request including parameters in a JSON dictionary. If there are no parameters required, then an empty dictionary is still required (or you get a 400 error).

Examples::

 curl http://test.ckan.net/api/action/package_list -d '{}'
 curl http://test.ckan.net/api/action/package_show -d '{"id": "fd788e57-dce4-481c-832d-497235bf9f78"}'

GET-able Actions
................

Actions defined in get.py can also be accessed with a GET request **in
addition** to the POST method described just above.

Each parameter is specified as a url parameter, for example: ::

 curl http://test.ckan.net/api/3/action/package_search?q=police

Or if the action expects a list of string for a given paramter, then that
parameter may be specified more than once, for example: ::

 curl http://test.ckan.net/api/3/action/term_translation_show?terms=russian&terms=romantic%20novel

will result in the following parameters being sent to the
`term_translation_show` action: ::

  {
    'terms': ['russian', 'romantic novel']
  }

This interface is *slightly* more limited than the POST interface because it
doesn't allow passing nested dicts into the action be accessed.  As a
consequence of this, currently the *resource_search* action is **limited** in
its functionality when accessed with a GET request.

`resource_search`:
    This action is not currently usable via a GET request as it relies upon
    a nested dict of fields.

Also, it is worth bearing this limitation in mind when creating your own
actions via the `IActions` interface.

Actions
=======

.. automodule:: ckan.logic.action.get
   :members:

.. automodule:: ckan.logic.action.create
   :members:

.. automodule:: ckan.logic.action.update
   :members:

.. automodule:: ckan.logic.action.delete
   :members:

In case of doubt, refer to the code of the logic actions, which is found in the CKAN source in the ``ckan/logic/action`` directory.

Responses
=========

The response is wholly contained in the form of a JSON dictionary. Here is the basic format of a successful request::

 {"help": "Creates a package", "success": true, "result": ...}

And here is one that incurred an error::

 {"help": "Creates a package", "success": false, "error": {"message": "Access denied", "__type": "Authorization Error"}}

Where:

* ``help`` is the 'doc string' (or ``null``)
* ``success`` is ``true`` or ``false`` depending on whether the request was successful. The response is always status 200, so it is important to check this value.
* ``result`` is the main payload that results from a successful request. This might be a list of the domain object names or a dictionary with the particular domain object.
* ``error`` is supplied if the request was not successful and provides a message and __type. See the section on errors.

Errors
======

The message types include:
  * Authorization Error - an API key is required for this operation, and the corresponding user needs the correct credentials
  * Validation Error - the object supplied does not meet with the standards described in the schema.
  * (TBC) JSON Error - the request could not be parsed / decoded as JSON format, according to the Content-Type (default is ``application/x-www-form-urlencoded;utf-8``).

Examples
========

::

 $ curl http://ckan.net/api/action/package_show -d '{"id": "fd788e57-dce4-481c-832d-497235bf9f78"}'
 {"help": null, "success": true, "result": {"maintainer": null, "name": "uk-quango-data", "relationships_as_subject": [], "author": null, "url": "http://www.guardian.co.uk/news/datablog/2009/jul/07/public-finance-regulators", "relationships_as_object": [], "notes": "### About\r\n\r\nDid you know there are nearly 1,200 unelected bodies with power over our lives? This is the full list, complete with number of staff and how much they cost. As a spreadsheet\r\n\r\n### Openness\r\n\r\nNo licensing information found.", "title": "Every Quango in Britain", "maintainer_email": null, "revision_timestamp": "2010-12-21T15:26:17.345502", "author_email": null, "state": "active", "version": null, "groups": [], "license_id": "notspecified", "revision_id": "f645243a-7334-44e2-b87c-64231700a9a6", "tags": [{"revision_timestamp": "2009-08-08T12:46:40.920443", "state": "active", "id": "b10871ea-b4ae-4e2e-bec9-a8d8ff357754", "name": "country-uk"}, {"revision_timestamp": "2009-08-08T12:46:40.920443", "state": "active", "id": "ed783bc3-c0a1-49f6-b861-fd9adbc1006b", "name": "quango"}], "id": "fd788e57-dce4-481c-832d-497235bf9f78", "resources": [{"resource_group_id": "49ddadb0-dd80-9eff-26e9-81c5a466cf6e", "hash": null, "description": "", "format": "", "url": "http://spreadsheets.google.com/ccc?key=tm4Dxoo0QtDrEOEC1FAJuUg", "revision_timestamp": "2011-07-08T14:48:38.967741", "state": "active", "position": 0, "revision_id": "188ac88b-1573-48bf-9ea6-d3c503db5816", "id": "888d00e9-6ee5-49ca-9abb-6f216e646345"}], "extras": []}}

Search API
~~~~~~~~~~

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

The Action API aims to return status ``200 OK``, whether there are errors or not. The response body contains the `success` field indicating whether an error occurred or not. When ``"success": false`` then you will receive details of the error in the `error` field. For example requesting a dataset that doesn't exist::

 curl http://test.ckan.net/api/action/package_show -d '{"id": "unknown_id"}'

gives::

 {"help": null, "success": false, "error": {"message": "Not found", "__type": "Not Found Error"}}

Alternatively, requests to the Action API that have major formatting problems may result in a 409, 400, or 500 error (in order of increasing severity), but future CKAN releases aim to avoid these responses in favour of the previously described method of providing the error message.

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

