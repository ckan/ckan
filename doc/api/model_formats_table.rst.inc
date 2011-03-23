+--------------------+------------------------------------------------------------+
| Name               | Format                                                     |
+====================+============================================================+
| Package-List       | |format-package-register|                                  |
+--------------------+------------------------------------------------------------+
| Package            | |format-package-entity|                                    |
|                    | See note below on additional fields upon GET of a package. |
+--------------------+------------------------------------------------------------+
| Group-List         | |format-group-register|                                    |
+--------------------+------------------------------------------------------------+
| Group              | |format-group-entity|                                      |
+--------------------+------------------------------------------------------------+
| Tag-List           | [ Name-String, Name-String, Name-String, ... ]             |
+--------------------+------------------------------------------------------------+
| Tag                | { name: Name-String }                                      |
+--------------------+------------------------------------------------------------+
| Resource           | { url: String, format: String, description: String,        |
|                    | hash: String }                                             |
+--------------------+------------------------------------------------------------+
| Rating             | { package: Name-String, rating: int }                      |
+--------------------+------------------------------------------------------------+
| Pkg-Relationships  | [ Pkg-Relationship, Pkg-Relationship, ... ]                |
+--------------------+------------------------------------------------------------+
| Pkg-Relationship   | { subject: Package-Name-String,                            |
|                    | object: Package-Name-String, type: Relationship-Type,      |
|                    | comment: String }                                          |
+--------------------+------------------------------------------------------------+
|Relationship-Type   | One of: 'depends_on', 'dependency_of',                     |
|                    | 'derives_from', 'has_derivation',                          |
|                    | 'child_of', 'parent_of'.                                   |
+--------------------+------------------------------------------------------------+
| Revision           | { id: Uuid, message: String, author: String,               |
|                    | timestamp: Date-Time, packages: Package-List }             |
+--------------------+------------------------------------------------------------+
| License-List       | [ License, License, License, ... ]                         |
+--------------------+------------------------------------------------------------+
| License            | { id: Name-String, title: String, is_okd_compliant:        |
|                    | Boolean, is_osi_compliant: Boolean, tags: Tag-List,        |
|                    | family: String, url: String, maintainer: String,           |
|                    | date_created: Date-Time, status: String }                  |
+--------------------+------------------------------------------------------------+

