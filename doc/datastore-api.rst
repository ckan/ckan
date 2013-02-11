=================
The DataStore API
=================

The DataStore API allows tabular data to be stored inside CKAN quickly and
easily. Making a DataStore API request is the same as making an Action API
request: you post a JSON dictionary in an HTTP POST request to an API URL, and
the API also returns its response in a JSON dictionary. See the
:ref:`action-api` for details.

Each resource in a CKAN instance can have an associated DataStore 'table'. The
basic API for accessing the DataStore is outlined below.

Quickstart
==========

There are several endpoints into the DataStore API, they are:

:meth:`~ckanext.datastore.logic.action.datastore_create`
  at ``http://{YOUR-CKAN-INSTALLATION}/api/action/datastore_create``
:meth:`~ckanext.datastore.logic.action.datastore_delete`
  at ``http://{YOUR-CKAN-INSTALLATION}/api/action/datastore_delete``
:meth:`~ckanext.datastore.logic.action.datastore_upsert`
  at ``http://{YOUR-CKAN-INSTALLATION}/api/action/datastore_upsert``
:meth:`~ckanext.datastore.logic.action.datastore_search`
  at ``http://{YOUR-CKAN-INSTALLATION}/api/action/datastore_search``
:meth:`~ckanext.datastore.logic.action.datastore_search_sql`, not available in :ref:`legacy mode<legacy_mode>`
  at ``http://{YOUR-CKAN-INSTALLATION}/api/action/datastore_search_sql``
``datastore_search_htsql()``, see :ref:`datastore_search_htsql`
  at ``http://{YOUR-CKAN-INSTALLATION}/api/action/datastore_search_htsql``

To understand the differences between the three last API endpoints, see :ref:`comparison_querying`.

API Reference
=============

The datastore related API actions are accessed via CKAN's :ref:`action-api`. When POSTing
requests, parameters should be provided as JSON objects.

.. note:: Lists can always be expressed in different ways. It is possible to use lists, comma separated strings or single items. These are valid lists: ``['foo', 'bar']``, ``'foo, bar'``, ``"foo", "bar"`` and ``'foo'``. Additionally, there are several ways to define a boolean value. ``True``, ``on`` and ``1`` are all vaid boolean values.

.. note:: The table structure of the DataStore is explained in :ref:`db_internals`.

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

.. _resource_aliases:

Resource aliases
----------------

A resource in the DataStore can have multiple aliases that are easier to remember than the resource id. Aliases can be created and edited with the :meth:`~ckanext.datastore.logic.action.datastore_create` API endpoint. All aliases can be found in a special view called ``_table_metadata``. See :ref:`db_internals` for full reference.

.. _datastore_search_htsql:

HTSQL Support
-------------


The `ckanext-htsql <https://github.com/okfn/ckanext-htsql>`_ extension adds an API action that allows a user to search data in a resource using the `HTSQL <http://htsql.org/doc/>`_ query expression language. Please refer to the extension documentation to know more.


.. _comparison_querying:

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
**Join resources**  No                                                        Yes                                                           Not yet
**Use aliases**                 Yes                                                       Yes                                                           Yes
==============================  ========================================================  ============================================================  =============================


.. _db_internals:

Internal structure of the database
----------------------------------

The DataStore is a thin layer on top of a PostgreSQL database. Each DataStore resource belongs to a CKAN resource. The name of a table in the DataStore is always the resource id of the CKAN resource for the data.

As explained in :ref:`resource_aliases`, a resource can have mnemonic aliases which are stored as views in the database.

All aliases (views) and resources (tables respectively relations) of the DataStore can be found in a special view called ``_table_metadata``. To access the list, open ``http://{YOUR-CKAN-INSTALLATION}/api/action/datastore_search?resource_id=_table_metadata``.

``_table_metadata`` has the following fields:

_id
    Unique key of the relation in ``_table_metadata``.
alias_of
    Name of a relation that this alias point to. This field is ``null`` iff the name is not an alias.
name
    Contains the name of the alias if alias_of is not null. Otherwise, this is the resource id of the CKAN resource for the DataStore resource.
oid
    The PostgreSQL object ID of the table that belongs to name.