======================
Testing for Developers
======================

If you are installing CKAN from source, or developing extensions, then you need to know how to run CKAN tests.

This section describes testing topics for developers, including basic tests, migration testing and testing against PostgreSQL. 

.. _basic-tests:

Basic Tests
-----------

After completing your source installation of CKAN, you should check that tests pass. You should also check this before checking in changes to CKAN code. 

Make sure you've created a config file at ``pyenv/ckan/development.ini``. Then activate the Python environment::

    . pyenv/bin/activate

Install nose and other test-specific dependencies into your virtual environment::

    pip install --ignore-installed -r pyenv/src/ckan/pip-requirements-test.txt

At this point you will need to deactivate and then re-activate your
virtual environment to ensure that all the scripts point to the correct
locations:

::

    deactivate
    . pyenv/bin/activate

Then run the quick development tests::

    cd pyenv/src/ckan
    nosetests ckan/tests --ckan

You *must* run the tests from the CKAN directory as shown above, otherwise the
``--ckan`` plugin won't work correctly. 

.. warning ::

   By default, the test run is 'quick and dirty' - only good enough as an initial check. 


Testing against PostgreSQL
--------------------------

The default way to run tests is defined in ``test.ini`` (which is the default config file for nose - change it with option ``--with-pylons``). This specifies using SQLite and sets ``faster_db_test_hacks``, which are compromises.

::

    cd pyenv/src/ckan
    nosetests ckan/tests --ckan

Although SQLite is useful for testing a large proportion of CKAN, actually in deployment, CKAN must run with PostgreSQL. 

Running the tests against PostgreSQL is slower but more thorough for two reasons:

 1. You test subtleties of PostgreSQL
 2. CKAN's default search relies on PostgreSQL's custom full-text search, so these (100 or so) tests are skipped when running against SQLite.

So when making changes to anything involved with search or closely related to the database, it is wise to test against PostgreSQL.

To test against PostgreSQL:

 1. Edit your local ``development.ini`` to specify a PostgreSQL database with the ``sqlalchemy.url`` parameter.
 2. Tell nose to use ``test-core.ini`` (which imports settings from ``development.ini``)

::

     nosetests ckan/tests --ckan --with-pylons=test-core.ini
 
The test suite takes a long time to run against standard PostgreSQL (approx. 15 minutes, or close to an hour on Ubuntu/10.04 Lucid).

This can be improved to between 5 and 15 minutes by running PostgreSQL in memory and turning off durability, as described `in the PostgreSQL documentation <http://www.postgresql.org/docs/9.0/static/non-durability.html>`_. 

.. _migrationtesting:

Migration Testing
-----------------

If your changes require a model change, you'll need to write a migration script. To ensure this is tested as well, you should instead run the tests this way::

     nosetests ckan/tests --ckan --ckan-migration --with-pylons=test-core.ini
 
By default, tests are run using the model defined in ``ckan/model``, but by using the ``--ckan-migration`` option the tests will run using a database that has been created using the migration scripts, which is the way the database is created and upgraded in production. These tests are the most thorough and will take around 20 minutes.

.. caution ::

    Ordinarily, you should set ``development.ini`` to specify a PostgreSQL database
    so these also get used when running ``test-core.ini``, since ``test-core.ini``
    inherits from ``development.ini``. If you were to change the ``sqlalchemy.url``
    option in your ``development.ini`` file to use SQLite, the command above would
    actually test SQLite rather than PostgreSQL, so always check the setting in
    ``development.ini`` to ensure you are running the full tests.

.. warning ::

   A common error when wanting to run tests against a particular database is to change ``sqlalchemy.url`` in ``test.ini`` or ``test-core.ini``. The problem is that these are versioned files and people have checked in these by mistake, creating problems for other developers and the CKAN buildbot. This is easily avoided by only changing ``sqlalchemy.url`` in your local ``development.ini`` and testing ``--with-pylons=test-core.ini``.

Testing Core Extensions
-----------------------

Some extensions are in the CKAN core codebase and have their own suite of tests. For example::

    nosetests --ckan ckanext/stats/tests

Common error messages
---------------------

Often errors are due to set-up errors. Always refer to the CKAN buildbot as the canonical build.

Consult :doc:`common-error-messages` for solutions to a range of setup problems.