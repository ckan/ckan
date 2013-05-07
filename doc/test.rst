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
created a config file at |development.ini|, then activate your
virtual environment:

.. parsed-literal::

    |activate|

Install nose and other test-specific CKAN dependencies into your virtual
environment:

.. parsed-literal::

    pip install -r |virtualenv|/src/ckan/pip-requirements-test.txt

Testing with SQLite
-------------------

To run the CKAN tests using SQLite as the database library:

.. parsed-literal::

    cd |virtualenv|/src/ckan
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

.. versionchanged:: 2.1
   Previously |postgres| tests used the databases defined in your
   ``development.ini`` file, instead of using their own test databases.

Create test databases:

.. parsed-literal::

    sudo -u postgres createdb -O |database_user| |test_database| -E utf-8
    sudo -u postgres createdb -O |database_user| |test_datastore| -E utf-8
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

ConfigError
```````````

``nose.config.ConfigError: Error reading config file 'setup.cfg': no such option 'with-pylons'``
   This error can result when you run nosetests for two reasons:

   1. Pylons nose plugin failed to run. If this is the case, then within a couple of lines of running `nosetests` you'll see this warning: `Unable to load plugin pylons` followed by an error message. Fix the error here first`.

   2. The Python module 'Pylons' is not installed into you Python environment. Confirm this with::

        python -c "import pylons"

OperationalError
````````````````

``OperationalError: (OperationalError) no such function: plainto_tsquery ...``
   This error usually results from running a test which involves search functionality, which requires using a PostgreSQL database, but another (such as SQLite) is configured. The particular test is either missing a `@search_related` decorator or there is a mixup with the test configuration files leading to the wrong database being used.

nosetests
`````````

``nosetests: error: no such option: --ckan``
   Nose is either unable to find ckan/ckan_nose_plugin.py in the python environment it is running in, or there is an error loading it. If there is an error, this will surface it::

         nosetests --version

   There are a few things to try to remedy this:

   Commonly this is because the nosetests isn't running in the python environment. You need to have nose actually installed in the python environment. To see which you are running, do this::

         which nosetests

   If you have activated the environment and this still reports ``/usr/bin/nosetests`` then you need to::

         pip install --ignore-installed nose

   If ``nose --version`` still fails, ensure that ckan is installed in your environment:

   .. parsed-literal::

         cd |virtualenv|/src/ckan
         python setup.py develop

   One final check - the version of nose should be at least 1.0. Check with::

         pip freeze | grep -i nose

