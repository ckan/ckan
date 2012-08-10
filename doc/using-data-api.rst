==================
Using the Data API
==================

The following provides an introduction to using the CKAN :doc:`DataStore
<datastore>` Data API.

Introduction
============

The DataStore API allows tabular data to be stored inside CKAN quickly and easily. It is accessible through an interface accessible over HTTP and can be interacted with using JSON (the JavaScript Object Notation).

.. raw:: html

   <iframe src="https://docs.google.com/presentation/embed?id=1UhEqvEPoL_VWO5okYiEPfZTLcLYWqtvRRmB1NBsWXY8&#038;start=false&#038;loop=false&#038;delayms=3000" frameborder="0" width="480" height="389" allowfullscreen="true" mozallowfullscreen="true" webkitallowfullscreen="true"></iframe>


Quickstart
==========

There are several endpoints into the DataStore API, they are:

* datastore_create: ``http://{YOUR-CKAN-INSTALLATION}/api/3/action/datastore_create``
* datastore_search: ``http://{YOUR-CKAN-INSTALLATION}/api/3/action/datastore_search``
* datastore_delete: ``http://{YOUR-CKAN-INSTALLATION}/api/3/action/datastore_delete``

Before going into detail about the API and the examples, it is useful to create a resource first so that you can store data against it in the Datastore. This can be done either through the CKAN Graphical User Interface.

Using the data API, we need to send JSON with this structure::

  { 
    id: Uuid, 
    name: Name-String, 
    title: String, 
    version: String, 
    url: String, 
    resources: [ { url: String, format: String, description: String, hash: String }, ...], 
    author: String, 
    author_email: String, 
    maintainer: String, 
    maintainer_email: String, 
    license_id: String, 
    tags: Tag-List, 
    notes: String, 
    extras: { Name-String: String, ... } 
 }

To the following endpoint:

* Dataset Model Endpoint: ``http://{YOUR-CKAN-INSTALLATION}/api/rest/dataset``

More details about creating a resource through the Data API are available on the :ref:`CKAN API page <api>`

API Reference
-------------

datastore_create
~~~~~~~~~~~~~~~~

The datastore_create API endpoint allows a user to post JSON data to 
be stored against a resource, the JSON must be in the following form::

 {
    resource_id: resource_id, # the data is going to be stored against.
    fields: [], # a list of dictionaries of fields/columns and their extra metadata.
    records: [], # a list of dictionaries of the data eg  [{"dob": "2005", "some_stuff": ['a', b']}, ..]
 }


datastore_search
~~~~~~~~~~~~~~~~

The datastore_search API endpoint allows a user to search data at a resource, 
the JSON for searching must be in the following form::

 {
     resource_id: # the resource id to be searched against
     filters : # dictionary of matching conditions to select e.g  {'key1': 'a. 'key2': 'b'}  
        # this will be equivalent to "select * from table where key1 = 'a' and key2 = 'b' "
     q: # full text query
     limit: # limit the amount of rows to size defaults to 20
     offset: # offset the amount of rows
     fields:  # list of fields return in that order, defaults (empty or not present) to all fields in fields order.
     sort: 
 }

datastore_delete
~~~~~~~~~~~~~~~~

The datastore_delete API endpoint allows a user to delete from a resource, 
the JSON for searching must be in the following form::

 {
    resource_id: resource_id # the data that is going to be deleted.
    filters: # dictionary of matching conditions to delete
       		# e.g  {'key1': 'a. 'key2': 'b'}  
       		# this will be equivalent to "delete from table where key1 = 'a' and key2 = 'b' "
 }


Examples
--------

Some of the following commands require obtaining an :ref:`API Key <get-api-key>`.

cURL (or Browser)
~~~~~~~~~~~~~~~~~

The following examples utilize the cURL_ command line utility. If you prefer,
you you can just open the relevant urls in your browser::

  # This creates a datastore
  curl -X POST {ENDPOINT:datastore_create} -H "Authorization: {YOUR-API-KEY}" -d "
    {\"resource_id\": \"{RESOURCE-ID}\", \"fields\": [ {\"id\": \"a\"}, {\"id\": \"b\"} ], 
    \"records\": [ { \"a\": 1, \"b\": \"xyz\"}, {\"a\": 2, \"b\": \"zzz\"} ]}"

  #This queries a datastore
  curl -X POST {ENDPOINT:datastore_search} -H "Authorization: {YOUR-API-KEY}" -d "
    {\"resource_id\": \"{RESOURCE-ID}\" }"

.. _cURL: http://curl.haxx.se/

Javascript
~~~~~~~~~~

Coming soon...

..
    A simple ajax (JSONP) request to the data API using jQuery::

      var data = {
        size: 5 // get 5 results
        q: 'title:jones' // query on the title field for 'jones'
      };
      $.ajax({
        url: {{endpoint}}/_search,
        dataType: 'jsonp',
        success: function(data) {
          alert('Total results found: ' + data.hits.total)
        }
      });

    The Data API supports CORs so you can also write to it (this requires the json2_ library for ``JSON.stringify``)::

      var data = {
        title: 'jones',
        amount: 5.7
      };
      $.ajax({
        url: {{endpoint}},
        type: 'POST',
        data: JSON.stringify(data),
        success: function(data) {
          alert('Uploaded ok')
        }
      });

    .. _json2: https://github.com/douglascrockford/JSON-js/blob/master/json2.js

Python
~~~~~~

Using the Python Requests_ library we can create a datastore like this::

 #! /usr/bin/env python
 
 import requests
 import json 
 
 auth_key = '<your-api-key>' 
 
 url = "http://127.0.0.1:5000/api/3/action/" # An example "action" endpoint
 
 datastore_structure = {
                         'resource_id': '<existing-resource-id>', 
                         'fields': [ {"id": "a"}, {"id": "b"} ], 
                         "records": [ { "a": 1, "b": "xyz"}, {"a": 2, "b": "zzz"} ]
                       }
 headers = {'content-type': 'application/json', 'Authorization': auth_key}
 r = requests.post(url + 'datastore_create', data=json.dumps(datastore_structure), headers=headers)
 print "done, and now for a quick search\n"

 datastore_structure = {
                         'resource_id': '<existing-resource-id>'
                       }
 headers = {'content-type': 'application/json', 'Authorization': auth_key}
 r = requests.post(url + 'datastore_search', data=json.dumps(datastore_structure), headers=headers) 
 
 print r.text
 
 print "done\n"


Python urllib2 version Coming soon...


.. _Requests: http://docs.python-requests.org/

PHP
~~~~~~

Coming soon...

