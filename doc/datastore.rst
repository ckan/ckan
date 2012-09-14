==========================
DataStore and the Data API
==========================

The CKAN DataStore provides a database for structured storage of data together
with a powerful Web-accesible Data API, all seamlessly integrated into the CKAN
interface and authorization system.

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

Each resource in a CKAN instance can have an associated DataStore 'table'. The
basic API for accessing the DataStore is detailed below. For a detailed
tutorial on using this API see :doc:`using-data-api`.

Installation and Configuration
==============================

The DataStore in previous lives required a custom setup of ElasticSearch and Nginx, 
but that is no more, as it can use any relational database management system 
(PostgreSQL for example).

In your config file ensure that the datastore extension is enabled::

 ckan.plugins = datastore
 
Also ensure that the ckan.datastore_write_url variable is set::

 ckan.datastore_write_url = postgresql://ckanuser:pass@localhost/ckantest
 
To test you can create a new datastore, so on linux command line do::

 curl -X POST http://127.0.0.1:5000/api/3/action/datastore_create -H "Authorization: {YOUR-API-KEY}"
   -d '{"resource_id": "{RESOURCE-ID}", "fields": [ {"id": "a"}, {"id": "b"} ], 
    "records": [ { "a": 1, "b": "xyz"}, {"a": 2, "b": "zzz"} ]}'


DataStorer: Automatically Add Data to the DataStore
===================================================

Often, one wants data that is added to CKAN (whether it is linked to or
uploaded to the :doc:`FileStore <filestore>`) to be automatically added to the
DataStore. This requires some processing, to extract the data from your files
and to add it to the DataStore in the format the DataStore can handle.

This task of automatically parsing and then adding data to the datastore is
performed by a DataStorer, a queue process that runs asynchronously and can be
triggered by uploads or other activities. The DataStorer is an extension and can
be found, along with installation instructions, at:

.. _datastorer: https://github.com/okfn/ckanext-datastorer


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

