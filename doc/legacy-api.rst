===========
Legacy APIs
===========

.. warning::

    The legacy APIs documented in this section are provided for
    backwards-compatibility, but support for new CKAN features will not be
    added to these APIs.


API Versions
~~~~~~~~~~~~

There are two versions of the legacy APIs. When the API returns a reference to
an object, version 1 of the API will return the name of the object (e.g.
``"river-pollution"``), whereas version 2 will return the ID of the object
(e.g.  ``"a3dd8f64-9078-4f04-845c-e3f047125028"``). Tag objects are an
exception, tag names are immutable so tags are always referred to with their
name.

You can specify which version of the API to use in the URL. For example,
opening this URL in your web browser will list demo.ckan.org's datasets using
API version 1:

http://demo.ckan.org/api/1/rest/dataset

Opening this URL calls the same function using API version 2:

http://demo.ckan.org/api/2/rest/dataset

If no version number is given in the URL then the API defaults to version 1, so
this URL will list the site's datasets using API version 1:

http://demo.ckan.org/api/rest/dataset

Dataset names can change, so to reliably refer to the same dataset over time,
you will want to use the dataset's ID and therefore use API v2. Alternatively,
many people prefer to deal with Names, so API v1 suits them.

When posting parameters with your API requests, you can refer to objects by
either their name or ID, interchangeably.


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
|                    | description: String, packages: Dataset-List }              |
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

.. Note::

 Only public datasets can be accessed via the legacy search API, regardless of
 the provided authorization. If you need to access private datasets via the
 API you will need to use the `package_search` method of the :doc:`api`.


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


Util API
~~~~~~~~

The Util API provides various utility APIs -- e.g. auto-completion APIs used by
front-end javascript.

All Util APIs are read-only. The response format is JSON. Javascript calls may
want to use the JSONP formatting.


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

