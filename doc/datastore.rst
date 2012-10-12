==========================
DataStore and the Data API
==========================

The CKAN DataStore provides a database for structured storage of data together
with a powerful Web-accessible Data API, all seamlessly integrated into the CKAN
interface and authorization system.

.. note:: The DataStore requires PostgreSQL 9.0 or later. It is possible to use the DataStore on versions prior to 9.0 (for example 8.4). However, the :meth:`~ckanext.datastore.logic.action.datastore_search_sql` will not be available and the set-up is slightly different. Make sure, you read :ref:`old_pg` for more details.


.. warning:: The DataStore does not support hiding resources in a private dataset.

.. _installation:

Installation and Configuration
==============================

.. warning:: Make sure that you follow the steps below and make sure that the settings are correct. Wrong settings could lead to serious security issues.

.. tip:: If these steps seem to complicated, the legacy mode can be used which does not require you to set the permissions or create a separate user. However, the legacy mode is limited in its capabilities.


The DataStore in previous lives required a custom set-up of ElasticSearch and Nginx,
but that is no more, as it now uses the relational database management system PostgreSQL.
However, you should set up a separate database for the DataStore
and create a read-only user to make your CKAN and DataStore installation safe.

1. Enable the extension
-----------------------

In your ``config`` file ensure that the ``datastore`` extension is enabled::

 ckan.plugins = datastore

2. Set-up the database
----------------------

The DataStore requires a separate postgres database to save the resources to.

List existing databases::

 sudo -u postgres psql -l

Check that the encoding of databases is ‘UTF8’, if not internationalisation may be a problem. Since changing the encoding of PostgreSQL may mean deleting existing databases, it is suggested that this is fixed before continuing with the CKAN install.

Next you will need to create a two database users for the DataStore. One user will be the *write* user that can create, edit and delete resources. The second user will be a *read-only* user who can only read resources.

A few things have to be kept in mind:

* The DataStore cannot be on the CKAN database (except for testing)
* The write user (i.e. ``writeuser``) and read-only user (i.e. ``readonlyuser``) cannot be the same

Create users and databases
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. tip:: The write user does not have to be created since you can also use the CKAN user. However, this might not be possible if the CKAN database and the DataStore database are on different servers. We recommend that you use the same user for CKAN and the write DataStore user if possible.

Create a write user called ``writeuser``, and enter pass for the password when prompted::

 sudo -u postgres createuser -S -D -R -P -l writeuser

Create a read-only user called ``readonlyuser``, and enter pass for the password when prompted::

 sudo -u postgres createuser -S -D -R -P -l readonlyuser

Create the database (owned by ``writeuser``), which we’ll call ``datastore``::

 sudo -u postgres createdb -O writeuser datastore

Set URLs
~~~~~~~~

Now, ensure that the ``ckan.datastore.write_url`` and ``datastore.read_url`` variables are set::

 ckan.datastore.write_url = postgresql://writeuser:pass@localhost/datastore
 ckan.datastore.read_url = postgresql://readonlyuser:pass@localhost/datastore

Set permissions
~~~~~~~~~~~~~~~

Once the DataStore database and the users are created, the permissions on the DataStore and CKAN database have to be set. Since there are different set-ups, there are different ways of setting the permissions. Only one of the options should be used.

1. Use the **paster command** if CKAN and PostgreSQL are on the same server

To set the permissions, use this paster command after you've set the database urls (make sure to have your virtualenv activated)::

 paster datastore set-permissions SQL_SUPER_USER


2. Use the **command line tool** in ``datastore/bin/datastore_setup.py``

.. note:: This option should be used if the CKAN server is different from the database server.

Copy the content from the ``datastore/bin/`` directory to the database server. Then run the command line tool to set the permissions on the database. To see all available options, run::

 python datastore_setup.py -h

Once you are confident that you know the right names, set the permissions (assuming that the CKAN database is called ``ckan`` and the CKAN PostgreSQL user is called ``ckanuser``)::

 python datastore_setup.py ckan datastore ckanuser writeuser readonlyuser -p postgres


3. Run the **SQL commands** manually on the database

.. note:: This option is for more complex set-ups and requires understanding of SQL and PostgreSQL.

Copy the ``set_permissions.sql`` file to the server that the database runs on. Make sure you set all variables in the file correctly and comment out the parts that are not needed for you set-up. Then, run the script::

 sudo -u postgres psql postgres -f set_permissions.sql


3. Test the set-up
------------------

The datastore is now set-up. To test the set-up you can create a new DataStore. To do so you can run the following command::

 curl -X POST http://127.0.0.1:5000/api/3/action/datastore_create -H "Authorization: {YOUR-API-KEY}" -d '{"resource_id": "{RESOURCE-ID}", "fields": [ {"id": "a"}, {"id": "b"} ], "records": [ { "a": 1, "b": "xyz"}, {"a": 2, "b": "zzz"} ]}'

A table named after the resource id should have been created on your DataStore
database. Visiting the following URL should return a response from the DataStore with
the records inserted above::

 http://127.0.0.1:5000/api/3/action/datastore_search?resource_id={RESOURCE_ID}


.. _old_pg:

Legacy mode: use the DataStore with old PostgreSQL versions
-----------------------------------------------------------

The DataStore can be used with a PostgreSQL version prior to 9.0 in *legacy mode*. Due to the lack of some functionality, the :meth:`~ckanext.datastore.logic.action.datastore_search_sql` and consequently the :ref:`datastore_search_htsql` cannot be used. The set-up for legacy mode is analogous to the normal set-up as described in :ref:`installation` with a few changes and consists of the following steps:

1. Enable the extension
#. Set-Up the database

    a) Create a separate database
    #) Create a write user on the DataStore database (optional since the CKAN user can be used)

#. Test the set-up

There is no need for a read-only user or special permissions. Therefore the legacy mode can be used for simple set-ups as well.

Relationship to FileStore
=========================

The DataStore is distinct but complementary to the FileStore (see
:doc:`filestore`). In contrast to the the FileStore which provides 'blob'
storage of whole files with no way to access or query parts of that file, the
DataStore is like a database in which individual data elements are accessible
and queryable. To illustrate this distinction, consider storing a spreadsheet
file like a CSV or Excel document. In the FileStore this file would be stored
directly. To access it you would download the file as a whole. By contrast, if
the spreadsheet data is stored in the DataStore, one would be able to access
individual spreadsheet rows via a simple web API, as well as being able to make
queries over the spreadsheet contents.


.. _datastorer:

DataStorer: Automatically Add Data to the DataStore
===================================================

Often, one wants data that is added to CKAN (whether it is linked to or
uploaded to the :doc:`FileStore <filestore>`) to be automatically added to the
DataStore. This requires some processing, to extract the data from your files
and to add it to the DataStore in the format the DataStore can handle.

This task of automatically parsing and then adding data to the DataStore is
performed by a DataStorer, a queue process that runs asynchronously and can be
triggered by uploads or other activities. The DataStorer is an extension and can
be found, along with installation instructions, at: https://github.com/okfn/ckanext-datastorer


The DataStore Data API
======================

The DataStore's Data API, which derives from the underlying data table,
is JSON-based with extensive query capabilities.

Each resource in a CKAN instance can have an associated DataStore 'table'. The
basic API for accessing the DataStore is outlined below. For a detailed
tutorial on using this API see :doc:`using-data-api`.


API Reference
-------------

The datastore related API actions are accessed via CKAN's :ref:`action-api`. When POSTing
requests, parameters should be provided as JSON objects.

.. note:: Lists can always be expressed in different ways. It is possible to use lists, comma separated strings or single items. These are valid lists: ``['foo', 'bar']``, ``'foo, bar'``, ``"foo", "bar"`` and ``'foo'``.

.. automodule:: ckanext.datastore.logic.action
   :members:



.. _fields:

Fields
~~~~~~

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
~~~~~~~

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
=============


The `ckanext-htsql <https://github.com/okfn/ckanext-htsql>`_ extension adds an API action that allows a user to search data in a resource using the `HTSQL <http://htsql.org/doc/>`_ query expression language. Please refer to the extension documentation to know more.



Comparison of different querying methods
========================================

The DataStore supports querying with multiple API endpoints. They are similar but support different features. The following list gives an overview of the different methods.

==============================  ========================================================  ============================================================  =============================
..                              :meth:`~ckanext.datastore.logic.action.datastore_search`  :meth:`~ckanext.datastore.logic.action.datastore_search_sql`  :ref:`datastore_search_htsql`
..                                                                                        SQL                                                           HTSQL
==============================  ========================================================  ============================================================  =============================
**Status**                      Stable                                                    Stable                                                        Available as extension
**Ease of use**                 Easy                                                      Complex                                                       Medium
**Flexibility**                 Low                                                       High                                                          Medium
**Query language**              Custom (JSON)                                             SQL                                                           HTSQL
**Connect multiple resources**  No                                                        Yes                                                           Not yet
**Use aliases**                 Yes                                                       Yes                                                           Yes
==============================  ========================================================  ============================================================  =============================
