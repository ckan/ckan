+-----------------+------------------------------------------------------------+
| Name            | Format                                                     |
+=================+============================================================+
| Package-List    | [ Id-String, Id-String, Id-String, ... ]                   |
+-----------------+------------------------------------------------------------+
| Package         | { name: Name-String, title: String, version: String,       |
|                 | url: String, resources: [ Resource, Resource, ...],        |
|                 | author: String, author_email: String,                      |
|                 | maintainer: String, maintainer_email: String,              |
|                 | license_id: String, tags: Tag-List, notes: String,         |
|                 | extras: { Name-String: String, ... } }                     |
|                 | See note below on additional fields upon GET of a package. |
+-----------------+------------------------------------------------------------+
| Group-List      | [ Id-String, Id-String, Id-String, ... ]                   |
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


