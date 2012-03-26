=============================
CKAN API: Quickstart Tutorial
=============================

A quickstart tutorial for the CKAN API that walks through some of the main
features. For full details of the API see :doc:`api` and its 
:ref:`api-reference` section.

The following examples use the demonstration instance at http://test.ckan.org/.
You may obviously replace this with your own site.

Details of tools for accessing the API including client libraries can be found
in the :ref:`main API section here <tools-for-api>`.

Example queries
===============

Search
------

http://test.ckan.org/api/search/dataset?q=open+street+map

::

 {"count": 4, "results": ["uk-naptan-osm", "osm-uk", "osm", "naptan"]}

Get dataset
-----------

http://test.ckan.org/api/rest/dataset/osm

::

 {"id": "a3dd8f64-9078-4f04-845c-e3f047125028", "name": "osm", "title": "Open Street Map", ...


Create a dataset
----------------

.. note:: You'll need an :ref:`api key <api-keys>`.

::

 curl http://test.ckan.org/api/rest/dataset -d '{"name":"test", "title":"Test dataset"}' -H "Authorization:your-api-key"

Update a dataset
----------------

(Using POST or PUT)::

  curl http://test.ckan.org/api/rest/dataset/test -d '{"name":"test", "title":"Changed Test dataset"}' -H "Authorization:your-api-key"

Viewing permissions
-------------------

To view authorization roles on a dataset::

  curl http://test.ckan.org/api/action/roles_show -d '{"domain_object": "freshwateratlasrivers"}'
  
  {
    "help": "Returns the roles that users (and authorization groups) have on a\n    particular domain_object.\n    \n    If you specify a user (or authorization group) then the resulting roles\n    will be filtered by those of that user (or authorization group).\n\n    domain_object can be a package/group/authorization_group name or id.\n    ", 
    "result": {
      "domain_object_id": "9da77628-2ac5-4965-af12-c7c51cc1d99a", 
      "domain_object_type": "Package", 
      "roles": [
        {
          "authorized_group_id": null, 
          "context": "Package", 
          "id": "481b6cd8-350b-4599-bd20-5e3c0ed0a8cb", 
          "package_id": "9da77628-2ac5-4965-af12-c7c51cc1d99a", 
          "role": "editor", 
          "user_id": "4229c297-fe28-4597-a191-3ebbbee6c47a", 
          "user_object_role_id": "481b6cd8-350b-4599-bd20-5e3c0ed0a8cb"
        }, 
        {
          "authorized_group_id": null, 
          "context": "Package", 
          "id": "aba38fa7-2fb4-4f84-98e1-02cb76c5d95a", 
          "package_id": "9da77628-2ac5-4965-af12-c7c51cc1d99a", 
          "role": "admin", 
          "user_id": "e7f30c0d-944b-4a69-84c4-61b08bbf6b98", 
          "user_object_role_id": "aba38fa7-2fb4-4f84-98e1-02cb76c5d95a"
        }, 
        {
          "authorized_group_id": null, 
          "context": "Package", 
          "id": "e06b1293-86ec-4417-8e28-b9499161348e", 
          "package_id": "9da77628-2ac5-4965-af12-c7c51cc1d99a", 
          "role": "reader", 
          "user_id": "41cb1162-3d61-4b16-a3af-4cae27836ac5", 
          "user_object_role_id": "e06b1293-86ec-4417-8e28-b9499161348e"
        }
      ]
    }, 
    "success": true
  }

Looking at the list of "roles" we can see who has what permissions on this
dataset. User with id="4229..." is an "editor", id="e7f3..." is an "admin",
"41cb..." is a "reader". By using the user_show call to reveal the names of the
users, we see that "visitor" (i.e. anyone who is not logged in) is the "reader"
(no write permission), "logged-in" (any logged-in user) is the "editor" and the
admin is "OKFN" who is the user who created this dataset in the first place and
can therefore confer permissions to other users.

Adding permissions
------------------

To give user "dread" the "admin" authorization role on dataset
"freshwateratlasrivers"::

  curl http://test.ckan.org/api/action/user_role_update -d '{"user": "dread", "domain_object": "freshwateratlasrivers", "roles": ["admin"]}' -H "Authorization:{your-api-key}"

Javascript examples
===================

See http://okfnlabs.org/ckanjs/ (demo search and count widgets)

