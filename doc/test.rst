======================
Testing for Developers
======================

If you're a CKAN developer, if you're developing an extension for CKAN, or if
you're just installing CKAN from source, you should make sure that CKAN's tests
pass for your copy of CKAN. This section explains how to run CKAN's tests.

.. _basic-tests:

Installing Additional Dependencies
----------------------------------

Some additional dependencies are needed to run the tests. Make sure you've
created a config file at ``~/pyenv/ckan/development.ini``, then activate your
virtual environment::

    . ~/pyenv/bin/activate

Install nose and other test-specific CKAN dependencies into your virtual
environment::

    pip install -r ~/pyenv/src/ckan/pip-requirements-test.txt

Testing with SQLite
-------------------

To run the CKAN tests using SQLite as the database library::

    cd ~/pyenv/src/ckan
    nosetests --ckan ckan

You *must* run the tests from the CKAN directory as shown above, otherwise the
``--ckan`` plugin won't work correctly.

In deployment CKAN uses PostgreSQL, not SQLite. Running the tests with SQLite
is less thorough but much quicker than with PostgreSQL, good enough for an
initial check but you should run the tests with PostgreSQL before deploying
anything or releasing any code.

Testing Core Extensions
```````````````````````

CKAN's core extensions (those extensions that are kept in the CKAN codebase
alongside CKAN itself) have their own tests. For example, to run the tests for
the stats extension do::

    nosetests --ckan ckanext/stats

To run the tests for all of the core extensions at once::

    nosetests --ckan ckanext

Or to run the CKAN tests and the core extensions tests together::

    nosetests --ckan ckan ckanext

Testing with PostgreSQL
-----------------------

Starting in CKAN 2.1 tests are run in a separate postgres database by
default.  You should create the test databases as follows.::

    sudo -u postgres createdb -O ckanuser ckan_test -E utf-8
    sudo -u postgres createdb -O ckanuser ckan_test_datastore -E utf-8
    # create datastore user default password `pass`
    sudo -u postgres createuser -S -D -R -P -l readonlyuser
    # set the permissions for readonly user
    paster datastore set-permissions postgres -c test-core.ini


This database connection is specified in the ``test-core.ini`` file by the
``sqlalchemy.url`` parameter.

CKAN's default nose configuration file (``test.ini``) specifies SQLite as the
database library (it also sets ``faster_db_test_hacks``). To run the tests more
thoroughly with PostgreSQL, specify the ``test-core.ini`` nose configuration
file instead, for example::

     nosetests --ckan --with-pylons=test-core.ini ckan
     nosetests --ckan --with-pylons=test-core.ini ckanext/stats
     nosetests --ckan --with-pylons=test-core.ini ckanext
     nosetests --ckan --with-pylons=test-core.ini ckan ckanext

The speed of the PostgreSQL tests can be improved by running PostgreSQL in
memory and turning off durability, as described
`in the PostgreSQL documentation <http://www.postgresql.org/docs/9.0/static/non-durability.html>`_. 

.. _migrationtesting:

Migration Testing
-----------------

If you're a CKAN developer or extension developer and your new code requires a
change to CKAN's model, you'll need to write a migration script. To ensure that
the migration script itself gets tested, you should run the tests with
they ``--ckan-migration`` option, for example::

     nosetests --ckan --ckan-migration --with-pylons=test-core.ini ckan

By default tests are run using the model defined in ``ckan/model``.
With the ``--ckan-migration`` option the tests will run using a database that
has been created by running the migration scripts in ``ckan/migration``, which
is how the database is created and upgraded in production.

.. warning ::

   A common error when wanting to run tests against a particular database is to
   change ``sqlalchemy.url`` in ``test.ini`` or ``test-core.ini``. The problem
   is that these are versioned files and people have checked in these by
   mistake, creating problems for other developers.

Common error messages
---------------------

Consult :doc:`common-error-messages` for solutions to a range of setup problems.
