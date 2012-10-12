======================
The DataStore Data API
======================

The following provides an introduction to using the CKAN :doc:`DataStore<datastore>` Data API.

The DataStore's Data API, which derives from the underlying data table, is JSON-based with extensive query capabilities.

Each resource in a CKAN instance can have an associated DataStore 'table'. The basic API for accessing the DataStore is outlined below.

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
:meth:`~ckanext.datastore.logic.action.datastore_search_sql`, not available in :ref:`legacy mode<legacy_mode>`
  at ``http://{YOUR-CKAN-INSTALLATION}/api/3/action/datastore_search_sql``
``datastore_search_htsql()``, see :ref:`datastore_search_htsql`
  at ``http://{YOUR-CKAN-INSTALLATION}/api/3/action/datastore_search_htsql``


API Reference
=============

The datastore related API actions are accessed via CKAN's :ref:`action-api`. When POSTing
requests, parameters should be provided as JSON objects.

.. note:: Lists can always be expressed in different ways. It is possible to use lists, comma separated strings or single items. These are valid lists: ``['foo', 'bar']``, ``'foo, bar'``, ``"foo", "bar"`` and ``'foo'``.

.. automodule:: ckanext.datastore.logic.action
   :members:



.. _fields:

Fields
------

Fields define the column names and the type of the data in a column. A field is defined as follows::

    {
        "id":    # a string which defines the column name
        "type":  # the data type for the column
    }

Field **types are optional** and will be guessed by the DataStore from the provided data. However, setting the types ensures that future inserts will not fail because of wrong types. See :ref:`valid-types` for details on which types are valid.

Example::

    [
        {
            "id": "foo",
            "type": "int4"
        },
        {
            "id": "bar"
            # type is optional
        }
    ]

.. _records:

Records
-------

A record is the data to be inserted in a table and is defined as follows::

    {
        "<id>":  # data to be set
        # .. more data
    }

Example::

    [
        {
            "foo": 100,
            "bar": "Here's some text"
        },
        {
            "foo": 42
        }
    ]

.. _valid-types:

Field types
-----------

The DataStore supports all types supported by PostgreSQL as well as a few additions. A list of the PostgreSQL types can be found in the `type section of the documentation`_. Below you can find a list of the most common data types. The ``json`` type has been added as a storage for nested data.

In addition to the listed types below, you can also use array types. They are defines by prepending a ``_`` or appending ``[]`` or ``[n]`` where n denotes the length of the array. An arbitrarily long array of integers would be defined as ``int[]``.

.. _type section of the documentation: http://www.postgresql.org/docs/9.1/static/datatype.html


text
    Arbitrary text data, e.g. ``Here's some text``.
json
    Arbitrary nested json data, e.g ``{"foo": 42, "bar": [1, 2, 3]}``.
    Please note that this type is a custom type that is wrapped by the DataStore.
date
    Date without time, e.g ``2012-5-25``.
time
    Time without date, e.g ``12:42``.
timestamp
    Date and time, e.g ``2012-10-01T02:43Z``.
int
    Integer numbers, e.g ``42``, ``7``.
float
    Floats, e.g. ``1.61803``.
bool
    Boolean values, e.g. ``true``, ``0``


You can find more information about the formatting of dates in the `date/time types section of the PostgreSQL documentation`_.

.. _date/time types section of the PostgreSQL documentation: http://www.postgresql.org/docs/9.1/static/datatype-datetime.html


Table aliases
-------------

A resource in the DataStore can have multiple aliases that are easier to remember than the resource id. Aliases can be created and edited with the datastore_create API endpoint. All aliases can be found in a special view called ``_table_metadata``.


.. _datastore_search_htsql:

HTSQL Support
-------------


The `ckanext-htsql <https://github.com/okfn/ckanext-htsql>`_ extension adds an API action that allows a user to search data in a resource using the `HTSQL <http://htsql.org/doc/>`_ query expression language. Please refer to the extension documentation to know more.



Comparison of different querying methods
----------------------------------------

The DataStore supports querying with multiple API endpoints. They are similar but support different features. The following list gives an overview of the different methods.

==============================  ========================================================  ============================================================  =============================
..                              :meth:`~ckanext.datastore.logic.action.datastore_search`  :meth:`~ckanext.datastore.logic.action.datastore_search_sql`  :ref:`HTSQL<datastore_search_htsql>`
==============================  ========================================================  ============================================================  =============================
**Status**                      Stable                                                    Stable                                                        Available as extension
**Ease of use**                 Easy                                                      Complex                                                       Medium
**Flexibility**                 Low                                                       High                                                          Medium
**Query language**              Custom (JSON)                                             SQL                                                           HTSQL
**Connect multiple resources**  No                                                        Yes                                                           Not yet
**Use aliases**                 Yes                                                       Yes                                                           Yes
==============================  ========================================================  ============================================================  =============================


Using the Data API
==================

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

