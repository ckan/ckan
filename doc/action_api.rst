.. index:: API

===========================
Reference: CKAN Action API
===========================

.. toctree::
   :hidden:
   :maxdepth: 1

.. warning:: The Action API is still experimental and subject to change of URI locations, formats, parameters and results.

Overview
--------

The Action API is a powerful RPC-style way of accessing CKAN data. Its intention is to have access to all the core logic in ckan. It calls exactly the same functions that are used internally which all the other CKAN interfaces (Web interface / Model API) go through. Therefore it provides the full gamut of read and write operations, with all possible parameters.

A client supplies parameters to the Action API via a JSON dictionary of a POST request, and returns results, help information and any error diagnostics in a JSON dictionary too. This is a departure from the CKAN API versions 1 and 2, which being RESTful required all the request parameters to be part of the URL.

Requests
--------

URL
===

The basic URL for the Action API is::

 /api/action/{logic_action}

Examples::
 
 /api/action/package_list
 /api/action/package_show
 /api/action/user_create

Actions
=======

get.py:

====================================== ===========================
Logic Action                           Parameter keys
====================================== ===========================
site_read                              (none)                      
package_list                           (none)
current_package_list_with_resources    limit
revision_list                          (none)
package_revision_list                  id
group_list                             all_fields
group_list_authz                       (none)
group_list_available                   (none)
group_revision_list                    id
licence_list                           (none)
tag_list                               q, all_fields, limit, offset, return_objects
user_list                              q, order_by
package_relationships_list             id, id2, rel
package_show                           id
revision_show                          id
group_show                             id
tag_show                               id
user_show                              id
package_show_rest                      id
group_show_rest                        id
tag_show_rest                          id
package_autocomplete                   q
tag_autocomplete                       q, limit
format_autocomplete                    q, limit
user_autocomplete                      q, limit
package_search                         q, fields, facet_by, limit, offset, filter_by_openness, filter_by_downloadable
====================================== ===========================

new.py: 

====================================== ===========================
Logic Action                           Parameter keys
====================================== ===========================
package_create                         (package keys)
package_create_validate                (package keys)
resource_create                        (resource keys)
package_relationship_create            id, id2, rel, comment
group_create                           (group keys)
rating_create                          package, rating
user_create                            (user keys)
package_create_rest                    (package keys)
group_create_rest                      (group keys)
====================================== ===========================

update.py:

====================================== ===========================
Logic Action                           Parameter keys
====================================== ===========================
make_latest_pending_package_active     id
resource_update                        (resource keys)
package_update                         (package keys)
package_update_validate                (package keys)
package_relationship_update            id, id2, rel, comment
group_update                           (group keys)
user_update                            (user keys), reset_key
package_update_rest                    (package keys)
group_update_rest                      (group keys)
====================================== ===========================

delete.py:

====================================== ===========================
Logic Action                           Parameter keys
====================================== ===========================
package_delete                         id
package_relationship_delete            id, id2, rel
group_delete                           id
====================================== ===========================

In case of doubt, refer to the code of the logic actions, which is found in the CKAN source in the ckan/logic/action directory.

Object dictionaries
===================

Package:

======================== ====================================== =============
key                      example value                          notes
======================== ====================================== =============
id                       "fd788e57-dce4-481c-832d-497235bf9f78" (Read-only) unique identifier
name                     "uk-spending"                          Unique identifier. Should be human readable
title                    "UK Spending"                          Human readable title of the dataset
url                      "http://gov.uk/spend-downloads.html"   Home page for the data
version                  "1.0"                                  Version associated with the data. String format.
author                   "UK Treasury"                          Name of person responsible for the data
author_email             "contact@treasury.gov.uk"              Email address for the person in the 'author' field
maintainer               null                                   Name of another person responsible for the data
maintainer_email         null                                   Email address for the person in the 'maintainer' field
notes                    "### About\\r\\n\\r\\nUpdated 1997."   Other human readable info about the dataset. Markdown format.
license_id               "cc-by"                                ID of the license this dataset is released under. You can then look up the license ID to get the title.
extras                   []                                      
tags                     ["government-spending"]                List of tags associated with this dataset.
groups                   ["spending", "country-uk"]             List of groups this dataset is a member of.
relationships_as_subject []                                     List of relationships (edit this only using relationship specific command). The 'type' of the relationship is described in terms of this package being the subject and the related package being the object.
state                    active                                 May be ``deleted`` or other custom states like ``pending``.
revision_id              "f645243a-7334-44e2-b87c-64231700a9a6" (Read-only) ID of the last revision for the core package object was (doesn't include tags, groups, extra fields, relationships).
revision_timestamp       "2010-12-21T15:26:17.345502"           (Read-only) Time and date when the last revision for the core package object was (doesn't include tags, groups, extra fields, relationships). ISO format. UTC timezone assumed.
======================== ====================================== =============

Package Extra:

======================== ====================================== =============
key                      example value                          notes
======================== ====================================== =============
id                       "c10fb749-ad46-4ba2-839a-41e8e2560687" (Read-only)
key                      "number_of_links"
value                    "10000"
package_id               "349259a8-cbff-4610-8089-2c80b34e27c5" (Read-only) Edit package extras with package_update
state                    "active"                               (Read-only) Edit package extras with package_update
revision_timestamp       "2010-09-01T08:56:53.696551"           (Read-only)
revision_id              "233d0c19-fcdc-44b9-9afe-25e2aa9d0a5f" (Read-only)
======================== ====================================== =============


Resource:

======================== ====================================== =============
key                      example value                          notes
======================== ====================================== =============
id                       "888d00e9-6ee5-49ca-9abb-6f216e646345" (Read-only)
url                      "http://gov.uk/spend-july-2009.csv"    Download URL of the data
description              ""
format                   "XLS"                                  Format of the data
hash                     null                                   Hash of the data e.g. SHA1
state                    "active"
position                 0                                      (Read-only) This is set by the order of resources are given in the list when creating/updating the package.
resource_group_id        "49ddadb0-dd80-9eff-26e9-81c5a466cf6e" (Read-only)
revision_id              "188ac88b-1573-48bf-9ea6-d3c503db5816" (Read-only)
revision_timestamp       "2011-07-08T14:48:38.967741"           (Read-only)
======================== ====================================== =============

Tag:

======================== ====================================== =============
key                      example value                          notes
======================== ====================================== =============
id                       "b10871ea-b4ae-4e2e-bec9-a8d8ff357754" (Read-only)
name                     "country-uk"                           (Read-only) Add/remove tags from a package or group using update_package or update_group
state                    "active"                               (Read-only) Add/remove tags from a package or group using update_package or update_group
revision_timestamp       "2009-08-08T12:46:40.920443"           (Read-only)
======================== ====================================== =============

Parameters
==========

Requests must be a POST, including parameters in a JSON dictionary. If there are no parameters required, then an empty dictionary is still required (or you get a 400 error).

Examples::

 curl http://test.ckan.net/api/action/package_list -d '{}'
 curl http://test.ckan.net/api/action/package_show -d '{"id": "fd788e57-dce4-481c-832d-497235bf9f78"}'

Authorization Header
====================

Authorization is carried out the same way as the existing API, supplying the user's API key in the "Authorization" header. 

Depending on the settings of the instance, you may not need to identify yourself for simple read operations. (This is the case for thedatahub.org and is assumed for the examples below.)

JSONP
=====

TBC

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