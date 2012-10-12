========================
Setting up the DataStore
========================

.. warning:: Make sure that you follow the steps below and make sure that the settings are correct. Wrong settings could lead to serious security issues.

.. note:: The DataStore requires PostgreSQL 9.0 or later. It is possible to use the DataStore on versions prior to 9.0 (for example 8.4). However, the :meth:`~ckanext.datastore.logic.action.datastore_search_sql` will not be available and the set-up is slightly different. Make sure, you read :ref:`legacy_mode` for more details.

.. warning:: The DataStore does not support hiding resources in a private dataset.


The :doc:`DataStore<datastore>` in previous lives required a custom set-up of ElasticSearch and Nginx,
but that is no more, as it now uses the relational database management system PostgreSQL.
However, you should set up a separate database for the DataStore
and create a read-only user to make your CKAN and DataStore installation safe.

1. Enable the extension
=======================

Since the DataStore is an optional extension, it has to be enabled separately. To do so, ensure that the ``datastore`` extension is enabled in your ``config`` file::

 ckan.plugins = datastore

2. Set-up the database
======================

The DataStore requires a separate PostgreSQL database to save the resources to.

List existing databases::

 sudo -u postgres psql -l

Check that the encoding of databases is ‘UTF8’, if not internationalisation may be a problem. Since changing the encoding of PostgreSQL may mean deleting existing databases, it is suggested that this is fixed before continuing with the CKAN install.

Next you will need to create a two database users for the DataStore. One user will be the *write* user that can create, edit and delete resources. The second user will be a *read-only* user who can only read resources.

A few things have to be kept in mind:

* The DataStore cannot be on the CKAN database (except for testing)
* The write user (i.e. ``writeuser``) and read-only user (i.e. ``readonlyuser``) cannot be the same

Create users and databases
--------------------------

.. tip:: The write user does not have to be created since you can also use the CKAN user. However, this might not be possible if the CKAN database and the DataStore database are on different servers. We recommend that you use the same user for CKAN and the write DataStore user if possible.

Create a write user called ``writeuser``, and enter pass for the password when prompted::

 sudo -u postgres createuser -S -D -R -P -l writeuser

Create a read-only user called ``readonlyuser``, and enter pass for the password when prompted::

 sudo -u postgres createuser -S -D -R -P -l readonlyuser

Create the database (owned by ``writeuser``), which we’ll call ``datastore``::

 sudo -u postgres createdb -O writeuser datastore

Set URLs
--------

Now, ensure that the ``ckan.datastore.write_url`` and ``ckan.datastore.read_url`` variables are set::

 ckan.datastore.write_url = postgresql://writeuser:pass@localhost/datastore
 ckan.datastore.read_url = postgresql://readonlyuser:pass@localhost/datastore

These URLs define how the DataStore connects to the PostgreSQL database. Having a read-only connections makes it possible to use the powerful PostgreSQL database directly.

Set permissions
---------------

.. tip:: See :ref:`legacy_mode` if these steps continue to fail or seem to complicated for your set-up. However, keep in mind that the legacy mode is limited in its capabilities.

Once the DataStore database and the users are created, the permissions on the DataStore and CKAN database have to be set. Since there are different set-ups, there are different ways of setting the permissions. Only **one** of the options should be used.

Option 1: Paster command
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This option is preferred if CKAN and PostgreSQL are on the same server.

To set the permissions, use this paster command after you've set the database URLs (make sure to have your virtualenv activated)::

 paster datastore set-permissions SQL_SUPER_USER


Option 2: Command line tool
~~~~~~~~~~~~~~~~~~~~~~~~~~~

This option should be used if the CKAN server is different from the database server.

Copy the content from the ``datastore/bin/`` directory to the database server. Then run the command line tool ``datastore_setup.py`` to set the permissions on the database. To see all available options, run::

 python datastore_setup.py -h

Once you are confident that you know the right names, set the permissions (assuming that the CKAN database is called ``ckan`` and the CKAN PostgreSQL user is called ``ckanuser``)::

 python datastore_setup.py ckan datastore ckanuser writeuser readonlyuser -p postgres


Option 3: SQL script
~~~~~~~~~~~~~~~~~~~~

This option is for more complex set-ups and requires understanding of SQL and PostgreSQL.

Copy the ``set_permissions.sql`` file to the server that the database runs on. Make sure you set all variables in the file correctly and comment out the parts that are not needed for you set-up. Then, run the script::

 sudo -u postgres psql postgres -f set_permissions.sql


3. Test the set-up
==================

The datastore is now set-up. To test the set-up you can create a new DataStore. To do so you can run the following command::

 curl -X POST http://127.0.0.1:5000/api/3/action/datastore_create -H "Authorization: {YOUR-API-KEY}" -d '{"resource_id": "{RESOURCE-ID}", "fields": [ {"id": "a"}, {"id": "b"} ], "records": [ { "a": 1, "b": "xyz"}, {"a": 2, "b": "zzz"} ]}'

A table named after the resource id should have been created on your DataStore
database. Visiting the following URL should return a response from the DataStore with
the records inserted above::

 http://127.0.0.1:5000/api/3/action/datastore_search?resource_id={RESOURCE_ID}

To find out more about the DataStore API, go to :doc:`datastore-api`.


.. _legacy_mode:

Legacy mode: use the DataStore with old PostgreSQL versions
===========================================================

.. tip:: The legacy mode can also be used to simplify the set-up since it does not require you to set the permissions or create a separate user.

The DataStore can be used with a PostgreSQL version prior to 9.0 in *legacy mode*. Due to the lack of some functionality, the :meth:`~ckanext.datastore.logic.action.datastore_search_sql` and consequently the :ref:`datastore_search_htsql` cannot be used. To enable the legacy mode, remove the declaration of the ``ckan.datastore.read_url``.

The set-up for legacy mode is analogous to the normal set-up as described above with a few changes and consists of the following steps:

1. Enable the extension
2. The legacy mode is enabled by **not** setting the ``ckan.datastore.read_url``
#. Set-Up the database

    a) Create a separate database
    #) Create a write user on the DataStore database (optional since the CKAN user can be used)

#. Test the set-up

There is no need for a read-only user or special permissions. Therefore the legacy mode can be used for simple set-ups as well.
