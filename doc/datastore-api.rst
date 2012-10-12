==================
Using the Data API
==================

The following provides an introduction to using the CKAN :doc:`DataStore
<datastore>` Data API.

Introduction
============

The DataStore API allows tabular data to be stored inside CKAN quickly and easily. It is accessible through an interface accessible over HTTP and can be interacted with using JSON (the JavaScript Object Notation).


Quickstart
==========

There are several endpoints into the DataStore API, they are:

:meth:`~ckanext.datastore.logic.action.datastore_create`
  at ``http://{YOUR-CKAN-INSTALLATION}/api/3/action/datastore_create``
:meth:`~ckanext.datastore.logic.action.datastore_delete`
  at ``http://{YOUR-CKAN-INSTALLATION}/api/3/action/datastore_delete``
:meth:`~ckanext.datastore.logic.action.datastore_upsert`
  at ``http://{YOUR-CKAN-INSTALLATION}/api/3/action/datastore_upsert``
:meth:`~ckanext.datastore.logic.action.datastore_search`
  at ``http://{YOUR-CKAN-INSTALLATION}/api/3/action/datastore_search``
:meth:`~ckanext.datastore.logic.action.datastore_search_sql`
  at ``http://{YOUR-CKAN-INSTALLATION}/api/3/action/datastore_search_sql``
``datastore_search_htsql()``, see :ref:`datastore_search_htsql`
  at ``http://{YOUR-CKAN-INSTALLATION}/api/3/action/datastore_search_htsql``

Before going into detail about the API and the examples, it is useful to create a resource first so that you can store data against it in the Datastore. This can be done either through the CKAN Graphical User Interface or the API.

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

More details about creating a resource through the Data API are available on the :ref:`CKAN API page <api>`. More information about the Datastore API can be found on the :doc:`datastore page <datastore>`.


Examples
--------

Some of the following commands require obtaining an :ref:`API Key <get-api-key>`.

cURL (or Browser)
~~~~~~~~~~~~~~~~~

The following examples utilize the cURL_ command line utility. If you prefer, you you can just open the relevant urls in your browser::

  # This creates a datastore
  curl -X POST <ENDPOINT:datastore_create> -H "Authorization: <YOUR-API-KEY>" -d '{"resource_id": "<RESOURCE-ID>", "fields": [ {"id": "a"}, {"id": "b"} ], "records": [ { "a": 1, "b": "xyz"}, {"a": 2, "b": "zzz"} ]}'


  #This queries a datastore
  curl "<ENDPOINT:datastore_search>?resource_id=<RESOURCE-ID>" -H "Authorization: <YOUR-API-KEY>"

.. _cURL: http://curl.haxx.se/

Javascript
~~~~~~~~~~

A simple ajax (JSONP) request to the data API using jQuery::

  $.ajax({
    url: '<ENDPOINT:datastore_search>',
    data: {'resource_id': '<RESOURCE-ID>'},
    dataType: 'jsonp',
    success: function(data) {
      alert('Total results found: ' + data.result.total)
    }
  });

The Data API supports CORs so you can also write to it (this requires the json2_ library for ``JSON.stringify``)::

  Coming soon...

..
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

A Python URLLib2 datastore_create and datastore_search would look like::

  #! /usr/bin/env python
  import urllib
  import urllib2
  import json

  auth_key = '<YOUR-API-KEY>'

  # In python using urllib2 for datastore_create it is...

  url = "<API-ENDPOINT>"

  datastore_structure = {
                  'resource_id': '<RESOURCE-ID>',
                  'fields': [{"id": "a"}, {"id": "b"}],
                  "records": [{"a": 12, "b": "abc"}, {"a": 2, "b": "zzz"}]
                }
  headers = {'content-type': 'application/json', 'Authorization': auth_key}

  req = urllib2.Request(url + 'datastore_create', data=json.dumps(datastore_structure), headers=headers)
  response = urllib2.urlopen(req)


  # in python for datastore_search using urllib2....

  datastore_structure = {
      'resource_id': '<RESOURCE-ID>'
    }

  url_values = urllib.urlencode(datastore_structure)
  req = urllib2.Request(url + 'datastore_search?' + url_values, headers=headers)
  response = urllib2.urlopen(req)

  print response.read()

  print "done\n"


Using the Python Requests_ library we can create a datastore like this::

 #! /usr/bin/env python

 import requests
 import json

 auth_key = '<YOUR-API-KEY>'

 url = '<API-ENDPOINT>'

 datastore_structure = {
                         'resource_id': '<RESOURCE-ID>',
                         'fields': [ {"id": "a"}, {"id": "b"} ],
                         "records": [ { "a": 1, "b": "xyz"}, {"a": 2, "b": "zzz"} ]
                       }
 headers = {'content-type': 'application/json', 'Authorization': auth_key}
 r = requests.post(url + 'datastore_create', data=json.dumps(datastore_structure), headers=headers)
 print "done, and now for a quick search\n"

 datastore_structure = {
                         'resource_id': '<RESOURCE-ID>'
                       }
 headers = {'content-type': 'application/json', 'Authorization': auth_key}
 r = requests.post(url + 'datastore_search', data=json.dumps(datastore_structure), headers=headers)

 print r.text

 print "done\n"


.. _Requests: http://docs.python-requests.org/

PHP
~~~~~~

::

  Coming soon...

