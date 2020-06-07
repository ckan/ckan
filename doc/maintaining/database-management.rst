.. _database management:

===================
Database Management
===================

.. note::

    See :doc:`cli` for details on running the ``ckan`` commands
    mentioned below.


.. _db init:

Initialization
--------------

Before you can run CKAN for the first time, you need to run ``db init`` to
initialize your database:

.. parsed-literal::

    ckan -c |ckan.ini| db init

If you forget to do this you'll see this error message in your web browser:

    503 Service Unavailable:  This site is currently off-line. Database is not
    initialised.


.. _db clean:

Cleaning
--------

.. warning::

   This will delete all data from your CKAN database!

You can delete everything in the CKAN database, including the tables, to start
from scratch:

.. parsed-literal::

    ckan -c |ckan.ini| db clean

After cleaning the database you must do either `initialize it`_ or `import
a previously created dump`_.

.. _initialize it: Initialization_
.. _import a previously created dump: `db dumping and loading`_


Import and Export
-----------------

.. _db dumping and loading:

Dumping and Loading databases to/from a file
````````````````````````````````````````````

PostgreSQL offers the command line tools pg_dump_ and pg_restore_ for dumping
and restoring a database and its content to/from a file.

For example, first dump your CKAN database::

    sudo -u postgres pg_dump --format=custom -d ckan_default > ckan.dump

.. warning::

   The exported file is a complete backup of the database, and includes API
   keys and other user data which may be regarded as private. So keep it
   secure, like your database server.

.. note::

    If you've chosen a non-default database name (i.e. *not* ``ckan_default``)
    then you need to adapt the commands accordingly.

Then restore it again:

.. parsed-literal::

    ckan -c |ckan.ini| db clean
    sudo -u postgres pg_restore --clean --if-exists -d ckan_default < ckan.dump

If you're importing a dump from an older version of CKAN you must :ref:`upgrade
the database schema <db upgrade>` after the import.

Once the import (and a potential upgrade) is complete you should :ref:`rebuild
the search index <rebuild search index>`.

.. _pg_dump: https://www.postgresql.org/docs/current/static/app-pgdump.html
.. _pg_restore: https://www.postgresql.org/docs/current/static/app-pgrestore.html


.. _datasets dump:

Exporting Datasets to JSON Lines
````````````````````````````````

You can export all of your CKAN site's datasets from your database to a JSON
Lines file using ckanapi_:

.. parsed-literal::

    ckanapi dump datasets -c |ckan.ini| -O my_datasets.jsonl

This is useful to create a simple public listing of the datasets, with no user
information. Some simple additions to the Apache config can serve the dump
files to users in a directory listing. To do this, add these lines to your
virtual Apache config file (e.g. |apache_config_file|)::

    Alias /dump/ /home/okfn/var/srvc/ckan.net/dumps/

    # Disable the mod_python handler for static files
    <Location /dump>
        SetHandler None
        Options +Indexes
    </Location>

.. warning::

   Don't serve an SQL dump of your database (created using the ``pg_dump``
   command), as those contain private user information such as email
   addresses and API keys.

.. _ckanapi: https://github.com/ckan/ckanapi


.. _users dump:

Exporting User Accounts to JSON Lines
`````````````````````````````````````

You can export all of your CKAN site's user accounts from your database to
a JSON Lines file using ckanapi_:

.. parsed-literal::

    ckanapi dump users -c |ckan.ini| -O my_database_users.jsonl


.. _db upgrade:

Upgrading
---------

.. warning::

    You should :ref:`create a backup of your database <db dumping and loading>`
    before upgrading it.

    To avoid problems during the database upgrade, comment out any plugins
    that you have enabled in your ini file. You can uncomment them again when
    the upgrade finishes.

If you are upgrading to a new CKAN :ref:`major release <releases>` update your
CKAN database's schema using the ``ckan db upgrade`` command:

.. parsed-literal::

    ckan -c |ckan.ini| db upgrade
