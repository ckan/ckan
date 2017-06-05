===================
DataStore extension
===================


The CKAN DataStore extension provides an *ad hoc* database for storage of structured data from
CKAN resources. Data can be pulled out of resource files and stored in
the DataStore.

When a resource is added to the DataStore, you get:

* Automatic data previews on the resource's page, using the :ref:`Data Explorer extension <data-explorer>`
* `The DataStore API`_: search, filter and update the data, without having to download
  and upload the entire data file

The DataStore is integrated into the :doc:`CKAN API </api/index>` and
authorization system.

The DataStore is generally used alongside the
`DataPusher <http://docs.ckan.org/projects/datapusher>`_, which will
automatically upload data to the DataStore from suitable files, whether
uploaded to CKAN's FileStore or externally linked.

.. contents::
   :depth: 1
   :local:

-------------------------
Relationship to FileStore
-------------------------

The DataStore is distinct but complementary to the FileStore (see
:doc:`filestore`). In contrast to the FileStore which provides 'blob'
storage of whole files with no way to access or query parts of that file, the
DataStore is like a database in which individual data elements are accessible
and queryable. To illustrate this distinction, consider storing a spreadsheet
file like a CSV or Excel document. In the FileStore this file would be stored
directly. To access it you would download the file as a whole. By contrast, if
the spreadsheet data is stored in the DataStore, one would be able to access
individual spreadsheet rows via a simple web API, as well as being able to make
queries over the spreadsheet contents.

------------------------
Setting up the DataStore
------------------------

.. note::

   The DataStore (like CKAN) requires |postgres| 9.2 or later. This was
   released in 2012, is widely available. At the time of writing, the only version
   that is not supported by CKAN that has not been made 'end-of-life' by the
   |postgres| community is 9.1.

.. versionchanged:: 2.6

   Previous CKAN (and DataStore) versions were compatible with earlier versions
   of |postgres|.

1. Enable the plugin
====================

Add the ``datastore`` plugin to your CKAN config file::

 ckan.plugins = datastore

2. Set-up the database
======================

.. warning:: Make sure that you follow the steps in `Set Permissions`_ below correctly. Wrong settings could lead to serious security issues.

The DataStore requires a separate PostgreSQL database to save the DataStore resources to.

List existing databases::

 sudo -u postgres psql -l

Check that the encoding of databases is ``UTF8``, if not internationalisation may be a problem. Since changing the encoding of PostgreSQL may mean deleting existing databases, it is suggested that this is fixed before continuing with the datastore setup.

Create users and databases
--------------------------

.. tip::

 If your CKAN database and DataStore databases are on different servers, then
 you need to create a new database user on the server where the DataStore
 database will be created. As in :doc:`installing/install-from-source` we'll
 name the database user |database_user|:

 .. parsed-literal::

    sudo -u postgres createuser -S -D -R -P -l |database_user|

Create a database_user called |datastore_user|. This user will be given
read-only access to your DataStore database in the `Set Permissions`_ step
below:

.. parsed-literal::

 sudo -u postgres createuser -S -D -R -P -l |datastore_user|

Create the database (owned by |database_user|), which we'll call
|datastore|:

.. parsed-literal::

 sudo -u postgres createdb -O |database_user| |datastore| -E utf-8

Set URLs
--------

Now, uncomment the :ref:`ckan.datastore.write_url` and
:ref:`ckan.datastore.read_url` lines in your CKAN config file and edit them
if necessary, for example:

.. parsed-literal::

 ckan.datastore.write_url = postgresql://|database_user|:pass@localhost/|datastore|
 ckan.datastore.read_url = postgresql://|datastore_user|:pass@localhost/|datastore|

Replace ``pass`` with the passwords you created for your |database_user| and
|datastore_user| database users.

Set permissions
---------------

.. tip:: See :ref:`legacy-mode` if these steps continue to fail or seem too complicated for your set-up. However, keep in mind that the legacy mode is limited in its capabilities.

Once the DataStore database and the users are created, the permissions on the DataStore and CKAN database have to be set. CKAN provides a paster command to help you correctly set these permissions.

If you are able to use the ``psql`` command to connect to your database as a
superuser, you can use the ``datastore set-permissions`` command to emit the
appropriate SQL to set the permissions.

For example, if you can connect to your database server as the ``postgres``
superuser using::

    sudo -u postgres psql

Then you can use this connection to set the permissions::

    sudo ckan datastore set-permissions | sudo -u postgres psql --set ON_ERROR_STOP=1

.. note::
   If you performed a source install, you will need to replace all references to
   ``sudo ckan ...`` with ``paster --plugin=ckan ...`` and provide the path to
   the config file, e.g. ``paster --plugin=ckan datastore set-permissions -c /etc/ckan/default/development.ini``

If your database server is not local, but you can access it over SSH, you can
pipe the permissions script over SSH::

    sudo ckan datastore set-permissions |
    ssh dbserver sudo -u postgres psql --set ON_ERROR_STOP=1

If you can't use the ``psql`` command in this way, you can simply copy and paste
the output of::

    sudo ckan datastore set-permissions

into a |postgres| superuser console.

3. Test the set-up
==================

The DataStore is now set-up. To test the set-up, (re)start CKAN and run the
following command to list all DataStore resources::

 curl -X GET "http://127.0.0.1:5000/api/3/action/datastore_search?resource_id=_table_metadata"

This should return a JSON page without errors.

To test the whether the set-up allows writing, you can create a new DataStore resource.
To do so, run the following command::

 curl -X POST http://127.0.0.1:5000/api/3/action/datastore_create -H "Authorization: {YOUR-API-KEY}" -d '{"resource": {"package_id": "{PACKAGE-ID}"}, "fields": [ {"id": "a"}, {"id": "b"} ], "records": [ { "a": 1, "b": "xyz"}, {"a": 2, "b": "zzz"} ]}'

Replace ``{YOUR-API-KEY}`` with a valid API key and ``{PACKAGE-ID}`` with the
id of an existing CKAN dataset.

A table named after the resource id should have been created on your DataStore
database. Visiting this URL should return a response from the DataStore with
the records inserted above::

 http://127.0.0.1:5000/api/3/action/datastore_search?resource_id={RESOURCE_ID}

Replace ``{RESOURCE-ID}`` with the resource id that was returned as part of the
response of the previous API call.

You can now delete the DataStore table with::

    curl -X POST http://127.0.0.1:5000/api/3/action/datastore_delete -H "Authorization: {YOUR-API-KEY}" -d '{"resource_id": "{RESOURCE-ID}"}'

To find out more about the DataStore API, see `The DataStore API`_.


.. _legacy-mode:

Legacy mode: use the DataStore with old PostgreSQL versions
===========================================================

.. tip:: The legacy mode can also be used to simplify the set-up since it does not require you to set the permissions or create a separate user.

The DataStore can be used with a PostgreSQL version prior to 9.0 in *legacy mode*. Due to the lack of some functionality, the :meth:`~ckanext.datastore.logic.action.datastore_search_sql` and consequently the :ref:`datastore_search_htsql` cannot be used. To enable the legacy mode, remove the declaration of the ``ckan.datastore.read_url``.

The set-up for legacy mode is analogous to the normal set-up as described above with a few changes and consists of the following steps:

1. Enable the plugin
2. The legacy mode is enabled by **not** setting the ``ckan.datastore.read_url``
#. Set-Up the database

   a) Create a separate database
   #) Create a write user on the DataStore database (optional since the CKAN user can be used)

#. Test the set-up

There is no need for a read-only user or special permissions. Therefore the legacy mode can be used for simple set-ups as well.


---------------------------------------------------
DataPusher: Automatically Add Data to the DataStore
---------------------------------------------------

Often, one wants data that is added to CKAN (whether it is linked to or
uploaded to the :doc:`FileStore <filestore>`) to be automatically added to the
DataStore. This requires some processing, to extract the data from your files
and to add it to the DataStore in the format the DataStore can handle.

This task of automatically parsing and then adding data to the DataStore is
performed by the `DataPusher`_, a service that runs asynchronously and can be installed
alongside CKAN.

To install this please look at the docs here: http://docs.ckan.org/projects/datapusher


-----------------
The DataStore API
-----------------

The CKAN DataStore offers an API for reading, searching and filtering data without
the need to download the entire file first. The DataStore is an ad hoc database which
means that it is a collection of tables with unknown relationships. This allows
you to search in one DataStore resource (a *table* in the database) as well as queries
across DataStore resources.

Data can be written incrementally to the DataStore through the API. New data can be
inserted, existing data can be updated or deleted. You can also add a new column to
an existing table even if the DataStore resource already contains some data.

Triggers may be added to enforce validation, clean data as it is loaded or
even record record histories. Triggers are PL/pgSQL functions that must be
created by a sysadmin.

You will notice that we tried to keep the layer between the underlying PostgreSQL
database and the API as thin as possible to allow you to use the features you would
expect from a powerful database management system.

A DataStore resource can not be created on its own. It is always required to have an
associated CKAN resource. If data is stored in the DataStore, it will automatically be
previewed by the :ref:`recline preview extension <data-explorer>`.


Making a DataStore API request
==============================

Making a DataStore API request is the same as making an Action API request: you
post a JSON dictionary in an HTTP POST request to an API URL, and the API also
returns its response in a JSON dictionary. See the :doc:`/api/index` for details.


API reference
=============

.. note:: Lists can always be expressed in different ways. It is possible to use lists, comma separated strings or single items. These are valid lists: ``['foo', 'bar']``, ``'foo, bar'``, ``"foo", "bar"`` and ``'foo'``. Additionally, there are several ways to define a boolean value. ``True``, ``on`` and ``1`` are all vaid boolean values.

.. note:: The table structure of the DataStore is explained in :ref:`db_internals`.

.. automodule:: ckanext.datastore.logic.action
   :members:


.. _dump:

Download resource
-----------------

A DataStore resource can be downloaded in the `CSV`_ file format from ``{CKAN-URL}/datastore/dump/{RESOURCE-ID}``.

For an Excel-compatible CSV file use ``{CKAN-URL}/datastore/dump/{RESOURCE-ID}?bom=true``.

Other formats supported include tab-separated values (``?format=tsv``),
JSON (``?format=json``) and XML (``?format=xml``). E.g. to download an Excel-compatible
tab-separated file use
``{CKAN-URL}/datastore/dump/{RESOURCE-ID}?format=tsv&bom=true``.

.. _CSV: https://en.wikipedia.org/wiki/Comma-separated_values


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

A record is the data to be inserted in a DataStore resource and is defined as follows::

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

.. _resource-aliases:

Resource aliases
----------------

A resource in the DataStore can have multiple aliases that are easier to remember than the resource id. Aliases can be created and edited with the :meth:`~ckanext.datastore.logic.action.datastore_create` API endpoint. All aliases can be found in a special view called ``_table_metadata``. See :ref:`db_internals` for full reference.

.. _datastore_search_htsql:

HTSQL support
-------------


The `ckanext-htsql <https://github.com/okfn/ckanext-htsql>`_ extension adds an API action that allows a user to search data in a resource using the `HTSQL <http://htsql.org/doc/>`_ query expression language. Please refer to the extension documentation to know more.


.. _comparison_querying:

Comparison of different querying methods
----------------------------------------

The DataStore supports querying with multiple API endpoints. They are similar but support different features. The following list gives an overview of the different methods.

==============================  ========================================================  ============================================================  =============================
..                              :meth:`~ckanext.datastore.logic.action.datastore_search`  :meth:`~ckanext.datastore.logic.action.datastore_search_sql`  :ref:`HTSQL<datastore_search_htsql>`
==============================  ========================================================  ============================================================  =============================
**Ease of use**                 Easy                                                      Complex                                                       Medium
**Flexibility**                 Low                                                       High                                                          Medium
**Query language**              Custom (JSON)                                             SQL                                                           HTSQL
**Join resources**              No                                                        Yes                                                           No
==============================  ========================================================  ============================================================  =============================


.. _db_internals:

Internal structure of the database
----------------------------------

The DataStore is a thin layer on top of a PostgreSQL database. Each DataStore resource belongs to a CKAN resource. The name of a table in the DataStore is always the resource id of the CKAN resource for the data.

As explained in :ref:`resource-aliases`, a resource can have mnemonic aliases which are stored as views in the database.

All aliases (views) and resources (tables respectively relations) of the DataStore can be found in a special view called ``_table_metadata``. To access the list, open ``http://{YOUR-CKAN-INSTALLATION}/api/3/action/datastore_search?resource_id=_table_metadata``.

``_table_metadata`` has the following fields:

_id
    Unique key of the relation in ``_table_metadata``.
alias_of
    Name of a relation that this alias point to. This field is ``null`` iff the name is not an alias.
name
    Contains the name of the alias if alias_of is not null. Otherwise, this is the resource id of the CKAN resource for the DataStore resource.
oid
    The PostgreSQL object ID of the table that belongs to name.

Extending DataStore
===================

Starting from CKAN version 2.7, backend used in DataStore can be replaced with custom one. For this purpose, custom extension must implement `ckanext.datastore.interfaces.IDatastoreBackend`, which provides one method - `register_backends`. It should return dictonary with names of custom backends as keys and classes, that represent those backends as values. Each class supposed to be inherited from `ckanext.datastore.backend.DatastoreBackend`.

.. note:: Example of custom implementation can be found at `ckanext.example_idatastorebackend`

.. automodule:: ckanext.datastore.backend
   :members:
