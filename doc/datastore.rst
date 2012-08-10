==========================
DataStore and the Data API
==========================

The CKAN DataStore provides a database for structured storage of data together
with a powerful Web-accesible Data API, all seamlessly integrated into the CKAN
interface and authorization system.

Overview
========

The following short set of slides provide a brief overview and introduction to
the DataStore and the Data API.

.. raw:: html

   <iframe src="https://docs.google.com/presentation/embed?id=1UhEqvEPoL_VWO5okYiEPfZTLcLYWqtvRRmB1NBsWXY8&#038;start=false&#038;loop=false&#038;delayms=3000" frameborder="0" width="480" height="389" allowfullscreen="true" mozallowfullscreen="true" webkitallowfullscreen="true"></iframe>

Relationship to FileStore
=========================

The DataStore is distinct but complementary to the FileStore (see
:doc:`filestore`). In contrast to the the FileStore which provides 'blob'
storage of whole files with no way to access or query parts of that file, the
DataStore is like a database in which individual data elements are accessible
and queryable. To illustrate this distinction consider storing a spreadsheet
file like a CSV or Excel document. In the FileStore this filed would be stored
directly. To access it you would download the file as a whole. By contrast, if
the spreadsheet data is stored in the DataStore one would be able to access
individual spreadsheet rows via a simple web-api as well as being able to make
queries over the spreadsheet contents.

The DataStore Data API
======================

The DataStore's Data API, which derives from the underlying data-table, 
is RESTful and JSON-based with extensive query capabilities.

Each resource in a CKAN instance has an associated DataStore 'table'. This
table will be accessible via a web interface at::

  /api/data/{resource-id}

For a detailed tutorial on using this API see :doc:`using-data-api`.

Installation and Configuration
==============================

The DataStore in previous lives required a custom setup of ElasticSearch and Nginx, 
but that is no more, as it can use any relational database management system 
(PostgreSQL for example).

To enable datastore features in CKAN
------------------------------------

In your config file ensure that the datastore extension is enabled::

 ckan.plugins = datastore
 
Also ensure that the ckan.datastore_write_url variable is set::

 ckan.datastore_write_url = postgresql://ckanuser:pass@localhost/ckantest
 
To test you can create a new datastore, so on linux command line do::

 curl -X POST http://127.0.0.1:5000/api/3/action/datastore_create -H "Authorization: {YOUR-API-KEY}" -d "
    {\"resource_id\": \"{RESOURCE-ID}\", \"fields\": [ {\"id\": \"a\"}, {\"id\": \"b\"} ], 
    \"records\": [ { \"a\": 1, \"b\": \"xyz\"}, {\"a\": 2, \"b\": \"zzz\"} ]}"



.. _datastorer:

DataStorer: Automatically Add Data to the DataStore
===================================================

Often, one wants data that is added to CKAN (whether it is linked to or uploaded to the :doc:`FileStore <filestore>`) to be automatically added to the
DataStore. This requires some processing, to extract the data from your files
and to add it to the DataStore in the format the DataStore can handle.

This task of automatically parsing and then adding data to the datastore is
performed by a DataStorer, a queue process that runs asynchronously and can be
triggered by uploads or other activities. The DataStorer is an extension and can
be found, along with installation instructions, at:

https://github.com/okfn/ckanext-datastorer


How It Works (Technically)
==========================

1. Request arrives at e.g. /dataset/{id}/resource/{resource-id}/data
2. CKAN checks authentication and authorization.
3. (Assuming OK) CKAN hands (internally) to the database querying system which handles the
   request 

