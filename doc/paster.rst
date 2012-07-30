.. _paster:

===============================
Common CKAN Administrator Tasks
===============================

The majority of common CKAN administration tasks are carried out using the **paster** script.

Paster is run on the command line on the server running CKAN. This section covers:

* :ref:`paster-understanding`. Understanding paster syntax and getting help.
* :ref:`paster-tasks`. How to carry out common CKAN admin tasks using paster.

.. _paster-understanding:

Understanding Paster
====================

At its simplest, paster commands can be thought of like this::

  paster <ckan commands>

But there are various extra elements to the commandline that usually need adding. We shall build them up:

Enabling CKAN commands
======================

Paster is used for many things aside from CKAN. You usually need to tell paster that you want to enable the CKAN commands::

  paster --plugin=ckan <ckan commands>

You know you need to do this if you get the error ``Command 'user' not known`` for a valid CKAN command.

(Alternatively, CKAN commands are enabled by default if your current directory is the CKAN source directory)

Pointing to your CKAN config
============================

Paster needs to know where your CKAN config file is (so it knows which database and search index to deal with etc.)::

  paster --plugin=ckan <ckan commands> --config=<config file>

If you forget to specify ``--config`` then you will get error ``AssertionError: Config filename '/home/okfn/development.ini' does not exist.``

(Paster defaults to looking for development.ini in the current directory.)

For example, to initialise a database::

  paster --plugin=ckan db init --config=/etc/ckan/std/std.ini

Virtual environments
====================

You often need to run paster within your CKAN virtual environment (pyenv). If CKAN was installed as 'source' then you can activate it as usual before running the paster command::

  . ~/pyenv/bin/activate
  paster --plugin=ckan db init --config=/etc/ckan/std/std.ini

The alternative, which also suits a CKAN 'package' install, is to simply give the full path to the paster in your pyenv::

  /var/lib/ckan/std/pyenv/bin/paster --plugin=ckan db init --config=/etc/ckan/std/std.ini


Running Paster on a deployment
==============================

If CKAN is deployed with Apache on this machine, then you should run paster as the same user, which is usually ``www-data``. This is because paster will write to the same CKAN logfile as the Apache process and file permissions need to match.

 For example::

  sudo -u www-data /var/lib/ckan/std/pyenv/bin/paster --plugin=ckan db init --config=/etc/ckan/std/std.ini

Otherwise you will get an error such as: ``IOError: [Errno 13] Permission denied: '/var/log/ckan/std/std.log'``.

.. _paster-help:

Getting Help on Paster
----------------------

To get a full list of paster commands (i.e. including CKAN commands)::

  paster --plugin=ckan --help

And to get more detailed help on each command (e.g. on ``db``)::

  paster --plugin=ckan --help db


Paster executable
-----------------

It is essential to run the correct paster. The program may be installed globally on a server, but in nearly all cases, the one installed in the CKAN python virtual environment (pyenv) is the one that should be used instead. This can be done by either:

1. Activating the virtual environment::

    . pyenv/bin/activate

2. Giving the path to paster when you run it::

    pyenv/bin/paster ...


Position of Paster Parameters
-----------------------------

The position of paster parameters matters.

``--plugin`` is a parameter to paster, so needs to come before the CKAN command. To do this, the first parameter to paster is normally ``--plugin=ckan``.

.. note:: The default value for ``--plugin`` is ``setup.py`` in the current directory. If you are running paster from the directory where CKAN's ``setup.py`` file is located, you don't need to specify the plugin parameter..

Meanwhile, ``--config`` is a parameter to CKAN, so needs to come after the CKAN command. This specifies the CKAN config file for the instance you want to use, e.g. ``--config=/etc/ckan/std/std.ini``

.. note:: The default value for ``--config`` is ``development.ini`` in the current directory. If you are running a package install of CKAN (as described in :doc:`install-from-package`), you should explicitly specify ``std.ini``.

The position of the CKAN command itself is less important, as longs as it follows ``--plugin``. For example, both the following commands have the same effect:::

  paster --plugin=ckan db --config=development.ini init
  paster --plugin=ckan db init --config=development.ini


Running a Paster Shell
----------------------

If you want to run a "paster shell", which can be useful for development, then the plugin is pylons. e.g. ``paster --plugin=pylons shell``.

Often you will want to run this as the same user as the web application, to ensure log files are written as the same user. And you'll also want to specify a config file (note that this is not specified using the ``--config`` parameter, but simply as the final argument). For example::

  sudo -u www-data paster --plugin=pylons shell std.ini


.. _paster-tasks:

Common Tasks Using Paster
=========================

The following tasks are supported by paster.

  ================= ==========================================================
  create-test-data  Create test data in the database.
  db                Perform various tasks on the database.
  ratings           Manage the ratings stored in the db
  rights            Commands relating to per-object and system-wide access rights.
  roles             Commands relating to roles and actions.
  search-index      Creates a search index for all datasets
  sysadmin          Gives sysadmin rights to a named user
  user              Manage users
  ================= ==========================================================


For the full list of tasks supported by paster, you can run::

 paster --plugin=ckan --help


create-test-data: Create test data
----------------------------------

As the name suggests, this command lets you load test data when first setting up CKAN. See :ref:`create-test-data` for details.


db: Manage databases
--------------------

Lets you initialise, upgrade, and dump the CKAN database.

Initialisation
~~~~~~~~~~~~~~

Before you can run CKAN for the first time, you need to run "db init" to create the tables in the database and the default authorization settings::

 paster --plugin=ckan db init --config=/etc/ckan/std/std.ini

If you forget to do this then CKAN won't serve requests and you will see errors such as this in the logs::

 ProgrammingError: (ProgrammingError) relation "user" does not exist

Cleaning
~~~~~~~~

You can delete everything in the CKAN database, including the tables, to start from scratch::

 paster --plugin=ckan db clean --config=/etc/ckan/std/std.ini

The next logical step from this point is to do a "db init" step before starting CKAN again.

.. _dumping and loading:

Dumping and Loading databases to/from a file
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can 'dump' (save) the exact state of the database to a file on disk and at a later point 'load' (restore) it again, or load it on another machine.

To write the dump::

 paster --plugin=ckan db dump --config=/etc/ckan/std/std.ini std.pg_dump

To load it in again, you first have to clean the database of existing data (be careful not to wipe valuable data), followed by the load::

 paster --plugin=ckan db clean --config=/etc/ckan/std/std.ini std.pg_dump
 paster --plugin=ckan db load --config=/etc/ckan/std/std.ini std.pg_dump

.. warning: The pg_dump file is a complete backup of the database in plain text, and includes API keys and other user data which may be regarded as private. So keep it secure, like your database server.

The pg_dump file notes which PostgreSQL user 'owns' the data on the server. Because the PostgreSQL user (by default) is identified as the current Linux user, and this is setup to be ``ckanINSTANCE`` where ``INSTANCE`` is the name of the CKAN instance. This means if you want to restore the pg_dump as another CKAN instance name (often needed if you move it to another server) then you will need to change the database owner - see :doc:`howto-editing-database-ownership`.

.. _upgrade migration:

Upgrade migration
~~~~~~~~~~~~~~~~~

When you upgrade CKAN software by any method *other* than the package update described in :doc:`install-from-package`, before you restart it, you should run 'db upgrade', which will do any necessary migrations to the database tables::

 paster --plugin=ckan db upgrade --config=/etc/ckan/std/std.ini

Creating dump files
~~~~~~~~~~~~~~~~~~~

For information on using ``db`` to create dumpfiles, see :doc:`database-dumps`.


ratings: Manage dataset ratings
-------------------------------

Manages the ratings stored in the database, and can be used to count ratings, remove all ratings, or remove only anonymous ratings.

For example, to remove anonymous ratings from the database::

 paster --plugin=ckan ratings clean-anonymous --config=/etc/ckan/std/std.ini


rights: Set user permissions
----------------------------

Sets the authorization roles of a specific user on a given object within the system.

For example, to give the user named 'bar' the 'admin' role on the dataset 'foo'::

 paster --plugin=ckan rights make bar admin package:foo  --config=/etc/ckan/std/std.ini

To list all the rights currently specified::

 paster --plugin=ckan rights list --config=/etc/ckan/std/std.ini

For more information and examples, see :doc:`authorization`.


roles: Manage system-wide permissions
--------------------------------------

This important command gives you fine-grained control over CKAN permissions, by listing and modifying the assignment of actions to roles.

The ``roles`` command has its own section: see :doc:`authorization`.

.. _rebuild search index:

search-index: Rebuild search index
----------------------------------

Rebuilds the search index. This is useful to prevent search indexes from getting out of sync with the main database.

For example::

 paster --plugin=ckan search-index rebuild --config=/etc/ckan/std/std.ini

This default behaviour will clear the index and rebuild it with all datasets. If you want to rebuild it for only
one dataset, you can provide a dataset name::

    paster --plugin=ckan search-index rebuild test-dataset-name --config=/etc/ckan/std/std.ini

Alternatively, you can use the `-o` or `--only-missing` option to only reindex datasets which are not
already indexed::

    paster --plugin=ckan search-index rebuild -o --config=/etc/ckan/std/std.ini

If you don't want to rebuild the whole index, but just refresh it, use the `-r` or `--refresh` option. This
won't clear the index before starting rebuilding it::

    paster --plugin=ckan search-index rebuild -r --config=/etc/ckan/std/std.ini

There are other search related commands, mostly useful for debugging purposes::

    search-index check                  - checks for datasets not indexed
    search-index show {dataset-name}    - shows index of a dataset
    search-index clear [dataset-name]   - clears the search index for the provided dataset or for the whole ckan instance



sysadmin: Give sysadmin rights
------------------------------

Gives sysadmin rights to a named user. This means the user can perform any action on any object.

For example, to make a user called 'admin' into a sysadmin::

 paster --plugin=ckan sysadmin add admin --config=/etc/ckan/std/std.ini


.. _paster-user:

user: Create and manage users
-----------------------------

Lets you create, remove, list and manage users.

For example, to create a new user called 'admin'::

 paster --plugin=ckan user add admin --config=/etc/ckan/std/std.ini

To delete the 'admin' user::

 paster --plugin=ckan user remove admin --config=/etc/ckan/std/std.ini
