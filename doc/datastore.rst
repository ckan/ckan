==========================
DataStore and the Data API
==========================

The CKAN DataStore provides a database for structured storage of data together
with a powerful Web-accessible Data API, all seamlessly integrated into the CKAN
interface and authorization system.

Installation and Configuration
==============================

.. warning:: Make sure that you follow the steps below and make sure that the settings are correct. Wrong settings could lead to serious security issues.

The DataStore in previous lives required a custom setup of ElasticSearch and Nginx,
but that is no more, as it the relational database management system PostgreSQL.
However, you should set-up a  separate database for the datastore
and create a read-only user to make your CKAN installation save.

In your ``config`` file ensure that the datastore extension is enabled::

 ckan.plugins = datastore

Also ensure that the ``ckan.datastore.write_url`` and ``datastore.read_url`` variables are set::

 ckan.datastore.write_url = postgresql://ckanuser:pass@localhost/datastore
 ckan.datastore.read_url = postgresql://readonlyuser:pass@localhost/datastore

A few things have to be kept in mind

* The datastore cannot be on the CKAN database (except for testing)
* The write user (i.e. ``ckanuser``) and read-only user (i.e. ``readonlyuser``) cannot be the same

To create a new database and a read-only user, use the provided paster commands after you have set the right database URLs.::

 paster --plugin=ckan datastore create-db <sql-user-user>
 paster --plugin=ckan datastore create-read-only-user <sql-user-user>

To test the setup you can create a new datastore, so on linux command line do::

 curl -X POST http://127.0.0.1:5000/api/3/action/datastore_create -H "Authorization: {YOUR-API-KEY}" -d '{"resource_id": "{RESOURCE-ID}", "fields": [ {"id": "a"}, {"id": "b"} ], "records": [ { "a": 1, "b": "xyz"}, {"a": 2, "b": "zzz"} ]}'


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


DataStorer: Automatically Add Data to the DataStore
===================================================

Often, one wants data that is added to CKAN (whether it is linked to or
uploaded to the :doc:`FileStore <filestore>`) to be automatically added to the
DataStore. This requires some processing, to extract the data from your files
and to add it to the DataStore in the format the DataStore can handle.

This task of automatically parsing and then adding data to the datastore is
performed by a DataStorer, a queue process that runs asynchronously and can be
triggered by uploads or other activities. The DataStorer is an extension and can
be found, along with installation instructions, at: https://github.com/okfn/ckanext-datastorer


The DataStore Data API
======================

The DataStore's Data API, which derives from the underlying data-table,
is RESTful and JSON-based with extensive query capabilities.

Each resource in a CKAN instance can have an associated DataStore 'table'. The
basic API for accessing the DataStore is detailed below. For a detailed
tutorial on using this API see :doc:`using-data-api`.


API Reference
-------------

.. note:: Lists can always be expressed in different ways. It is possible to use lists, comma separated strings or single items. These are valid lists: ``['foo', 'bar']``, ``foo, bar``, ``"foo", "bar"`` and ``foo``.


datastore_create
~~~~~~~~~~~~~~~~

The datastore_create API endpoint allows a user to post JSON data to
be stored against a resource. This endpoint also supports altering tables, aliases and indexes and bulk insertion.
The JSON must be in the following form::

 {
    resource_id: resource_id, # the data is going to be stored against.
    aliases: # list of names for read only aliases to the resource
    fields: [] # a list of dictionaries of fields/columns and their extra metadata.
    records: [] # a list of dictionaries of the data, eg:  [{"dob": "2005", "some_stuff": ['a', b']}, ..]
    primary_key: # list of fields that represent a unique key
    indexes: # indexes on table
 }

See :ref:`valid-types` for details on which types are valid.


datastore_delete
~~~~~~~~~~~~~~~~

The datastore_delete API endpoint allows a user to delete from a resource.
The JSON for searching must be in the following form::

 {
    resource_id: resource_id # the data that is going to be deleted.
    filter: # dictionary of matching conditions to delete
            # e.g  {'key1': 'a. 'key2': 'b'}
            # this will be equivalent to "delete from table where key1 = 'a' and key2 = 'b' "
 }


datastore_upsert
~~~~~~~~~~~~~~~~

The datastore_upsert API endpoint allows a user to add data to an existing datastore resource. In order for the upsert and update to work a unique key has to defined via the datastore_create API endpoint command.
The JSON for searching must be in the following form::

 {
    resource_id: resource_id # resource id that the data is going to be stored under.
    records: [] # a list of dictionaries of the data, eg:  [{"dob": "2005", "some_stuff": ['a', b']}, ..]
    method: # the method to use to put the data into the datastore
            # possible options: upsert (default), insert, update
 }

upsert
    Update if record with same key already exists, otherwise insert. Requires unique key.
insert
    Insert only. This method is faster that upsert because checks are omitted. Does *not* require a unique key.
update
    Update only. Exception will occur if the key that should be updated does not exist. Requires unique key.

datastore_search
~~~~~~~~~~~~~~~~

The datastore_search API endpoint allows a user to search data at a resource.
The JSON for searching must be in the following form::

 {
     resource_id: # the resource id to be searched against
     filters : # dictionary of matching conditions to select e.g  {'key1': 'a. 'key2': 'b'}
        # this will be equivalent to "select * from table where key1 = 'a' and key2 = 'b' "
     q: # full text query
     plain: # treat as plain text query (default: true)
     language: # language of the full text query (default: english)
     limit: # limit the amount of rows to size (default: 100)
     offset: # offset the amount of rows
     fields:  # list of fields return in that order, defaults (empty or not present) to all fields in fields order.
     sort: # ordered list of field names as, eg: "fieldname1, fieldname2 desc"
 }

datastore_search_sql
~~~~~~~~~~~~~~~~~~~~

The datastore_search_sql API endpoint allows a user to search data at a resource or connect multiple resources with join expressions. The underlying SQL engine is the `PostgreSQL engine <http://www.postgresql.org/docs/9.1/interactive/sql/.html>`_. The JSON for searching must be in the following form::

 {
    sql: # a single sql select statement
 }


datastore_search_htsql
~~~~~~~~~~~~~~~~~~~~~~

.. note:: HTSQL is not in the core datastore and has to be installed as a plugin.

The datastore_search_htsql API endpoint allows a user to search data at a resource using the `HTSQL <http://htsql.org/doc/>`_ query expression language. The JSON for searching must be in the following form::

 {
    htsql: # a htsql query statement.
 }

.. _valid-types:

Field types
-----------

The datastore supports all types supported by PostgreSQL as well as a few additions. A list of the PostgreSQL types can be found in the `documentation`_. Below you can find a list of the most common data types. The ``json`` type has been added as a storage for nested data.

.. _documentation: http://www.postgresql.org/docs/9.1/static/datatype.html


text
    Arbitrary text data, e.g. *I'm a text*.
date
    Date without time, e.g *2012-5-25*
time
    Time without date, e.g *12:42*
timestamp
    Date and time, e.g *2012-10-01T02:43Z*.
int4
    Integer numbers, e.g *42*, *7*.
float8
    Floats, e.g. *1.61803*.
bool
    Boolen values, e.g. *true*, *0*


Table aliases
-------------

Resources in the datastore can have multiple aliases that are easier to remember than the resource id. Aliases can be created and edited with the datastore_create API endpoint. All aliases can be found in a special view called ``_table_metadata``.

Comparison of different querying methods
----------------------------------------

The datastore supports querying with the datastore_search and datastore_search_sql API endpoint. They are similar but support different features. The following list gives an overview on the different methods.

==============================  =======================  =====================  ======================
..                              datastore_search         datastore_search_sql   datastore_search_htsql
..                                                       SQL                    HTSQL
==============================  =======================  =====================  ======================
**Status**                      Stable                   Stable                 Will be available as plugin
**Ease of use**                 Easy                     Complex                Medium
**Flexibility**                 Low                      High                   Medium
**Query language**              Custom (JSON)            SQL                    HTSQL
**Connect multiple resources**  No                       Yes                    Yes
**Use aliases**                 Yes                      Yes                    Yes
==============================  =======================  =====================  ======================