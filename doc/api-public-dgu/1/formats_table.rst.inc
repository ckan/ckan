+-------------------------+------------------------------------------------------------+
| Name                    | Format                                                     |
+=========================+============================================================+
| Package-List            | [ Name-String, Name-String, Name-String, ... ]             |
| (API v1 only)           |                                                            |
+-------------------------+------------------------------------------------------------+
| Package-List            | [ Id-String, Id-String, Id-String, ... ]                   |
| (API v2 only)           |                                                            |
+-------------------------+------------------------------------------------------------+
| Package                 | { name: Name-String, title: String, version: String,       |
|                         | url: String, resources: [ Resource, Resource, ...],        |
|                         | author: String, author_email: String,                      |
|                         | maintainer: String, maintainer_email: String,              |
|                         | license_id: String, tags: Tag-List, notes: String,         |
|                         | extras: { Name-String: String, ... } }                     |
+-------------------------+------------------------------------------------------------+
| Group-List              | [ Name-String, Name-String, Name-String, ... ]             | 
| (API v1 only)           |                                                            |
+-------------------------+------------------------------------------------------------+
| Group-List              | [ Id-String, Id-String, Id-String, ... ]                   |
| (API v2 only)           |                                                            |
+-------------------------+------------------------------------------------------------+
| Group                   | { name: Name-String, title: String, description: String,   | 
|                         | packages: Package-List }                                   |
+-------------------------+------------------------------------------------------------+
| Tag-List                | [ Name-String, Name-String, Name-String, ... ]             |
+-------------------------+------------------------------------------------------------+
| Tag                     | { name: Name-String }                                      |
+-------------------------+------------------------------------------------------------+
| Resource                | { url: String, format: String, description: String,        |
|                         | hash: String }                                             |
+-------------------------+------------------------------------------------------------+
| Rating                  | { package: Name-String, rating: int }                      |
+-------------------------+------------------------------------------------------------+
| Pkg-Relationships       | [ Pkg-Relationship, Pkg-Relationship, ... ]                |
+-------------------------+------------------------------------------------------------+
| Pkg-Relationship        | { subject: Package-Name-String,                            |
|                         | object: Package-Name-String, type: Relationship-Type,      |
|                         | comment: String }                                          |
+-------------------------+------------------------------------------------------------+
| Relationship-Type       | One of: 'depends_on', 'dependency_of',                     |
|                         | 'derives_from', 'has_derivation',                          |
|                         | 'child_of', 'parent_of'.                                   |
+-------------------------+------------------------------------------------------------+
| Revision                | { id: Uuid, message: String, author: String,               |
|                         | timestamp: Date-Time, packages: Package-List }             |
+-------------------------+------------------------------------------------------------+
| License-List            | [ License, License, License, ... ]                         |
+-------------------------+------------------------------------------------------------+
| License                 | { id: Name-String, title: String, is_okd_compliant:        |
|                         | Boolean, is_osi_compliant: Boolean, tags: Tag-List,        |
|                         | family: String, url: String, maintainer: String,           |
|                         | date_created: Date-Time, status: String }                  |
+-------------------------+------------------------------------------------------------+
| Name-String             | An alphanumeric string.                                    |
+-------------------------+------------------------------------------------------------+
| Package-Search-Params   | { Param-Key: Param-Value, Param-Key: Param-Value, ... }    |
| Resource-Search-Params  | See below for full details of search parameters across the | 
| Revision-Search-Params  | various domain objects.                                    |
+-------------------------+------------------------------------------------------------+
| Package-Search-Response | { count: Count-int, results: [Package, Package, ... ] }    |
+-------------------------+------------------------------------------------------------+
| Resource-Search-Response| { count: Count-int, results: [Resource, Resource, ... ] }  |
+-------------------------+------------------------------------------------------------+
| Revision-List           | [ Revision-Id, Revision-Id, Revision-Id, ... ]             |
|                         | NB: Ordered with youngest revision first                   |
+-------------------------+------------------------------------------------------------+
| Tag-Count-List          | [ [Name-String, Integer], [Name-String, Integer], ... ]    |
+-------------------------+------------------------------------------------------------+

It is also possible to supply the search parameters in the URL of a GET request, 
for example ``/search/package?q=geodata&amp;allfields=1``.


Todo: Repair Package Entity data format.

|                         | See note below on additional fields upon GET of a package. |
|                         | * When you read a package then some additional information is supplied that cannot current be adjusted throught the Public API. This includes info on Package Relationship ('relationships'), Group membership ('groups'), ratings ('ratings_average' and 'ratings_count') and Package ID ('id'). This is purely a convenience for clients, and only forms part of the Package on GET.|


Package Search Parameters
"""""""""""""""""""""""""

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


Resource Search Parameters
""""""""""""""""""""""""""

+-----------------------+---------------+-----------------------------------------+----------------------------------+
| Param-Key             | Param-Value   | Example                                 |  Notes                           |
+=======================+===============+=========================================+==================================+
| url, format,          | Search-String || url=statistics.org                     | Criteria to search the package   |
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


Revision Search Parameters
""""""""""""""""""""""""""

+-----------------------+---------------+-----------------------------------------------------+----------------------------------+
| Param-Key             | Param-Value   | Example                                             |  Notes                           |
+=======================+===============+=====================================================+==================================+ 
| since_time            | Date-Time     | since_time=2010-05-05T19:42:45.854533               | The time can be less precisely   |
|                       |               |                                                     | stated (e.g 2010-05-05).         |
+-----------------------+---------------+-----------------------------------------------------+----------------------------------+
| since_id              | Uuid          | since_id=6c9f32ef-1f93-4b2f-891b-fd01924ebe08       | The stated id will not be        |
|                       |               |                                                     | included in the results.         |
+-----------------------+---------------+-----------------------------------------------------+----------------------------------+


