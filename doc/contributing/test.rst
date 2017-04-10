============
Testing CKAN
============

If you're a CKAN developer, if you're developing an extension for CKAN, or if
you're just installing CKAN from source, you should make sure that CKAN's tests
pass for your copy of CKAN. This section explains how to run CKAN's tests.

CKAN's testsuite contains automated tests for both the back-end (Python) and
the front-end (JavaScript). In addition, the correct functionality of the
complete front-end (HTML, CSS, JavaScript) on all supported browsers should be
tested manually.

--------------
Back-end tests
--------------

Most of CKAN's testsuite is for the backend Python code.

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Install additional dependencies
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Some additional dependencies are needed to run the tests. Make sure you've
created a config file at |development.ini|, then activate your
virtual environment:

.. parsed-literal::

    |activate|

Install nose and other test-specific CKAN dependencies into your virtual
environment:

.. versionchanged:: 2.1
   In CKAN 2.0 and earlier the requirements file was called
   ``pip-requirements-test.txt``, not ``dev-requirements.txt`` as below.

.. parsed-literal::

    pip install -r |virtualenv|/src/ckan/dev-requirements.txt


~~~~~~~~~~~~~~~~~~~~~~~~~
Set up the test databases
~~~~~~~~~~~~~~~~~~~~~~~~~

.. versionchanged:: 2.1
   Previously |postgres| tests used the databases defined in your
   ``development.ini`` file, instead of using their own test databases.

Create test databases:

.. parsed-literal::

    sudo -u postgres createdb -O |database_user| |test_database| -E utf-8
    sudo -u postgres createdb -O |database_user| |test_datastore| -E utf-8
    paster datastore set-permissions -c test-core.ini | sudo -u postgres psql

This database connection is specified in the ``test-core.ini`` file by the
``sqlalchemy.url`` parameter.

You should also make sure that the :ref:`Redis database <ckan_redis_url>`
configured in ``test-core.ini`` is different from your production database.


.. _solr-multi-core:

~~~~~~~~~~~~~~~~~~~~~~~~~
Configure Solr Multi-core
~~~~~~~~~~~~~~~~~~~~~~~~~

The tests assume that Solr is configured 'multi-core', whereas the default
Solr set-up is often 'single-core'. You can ask Solr how many cores it has
configured::

    curl -s 'http://127.0.0.1:8983/solr/admin/cores?action=STATUS' |python -c 'import sys;import xml.dom.minidom;s=sys.stdin.read();print xml.dom.minidom.parseString(s).toprettyxml()'

You can also tell from your ckan config::

    grep solr_url /etc/ckan/default/production.ini
    # single-core: solr_url = http://127.0.0.1:8983/solr
    # multi-core:  solr_url = http://127.0.0.1:8983/solr/ckan

To enable multi-core:

1. Find the ``instanceDir`` of the existing Solr core. It is found in the output of the curl command above.

       e.g. ``/usr/share/solr/`` or ``/opt/solr/example/solr/collection1``

2. Make a copy of that core's directory e.g.::

       sudo cp -r /usr/share/solr/ /etc/solr/ckan

3. Configure Solr with the new core::

       curl 'http://localhost:8983/solr/admin/cores?action=CREATE&name=ckan&instanceDir=/etc/solr/ckan'

   If successful the status should be 0 - some XML containing: ``<int name="status">0</int>``

4. Edit your main ckan config (e.g. |development.ini|) and adjust the solr_url to match::

       solr_url = http://127.0.0.1:8983/solr/ckan


~~~~~~~~~~~~~
Run the tests
~~~~~~~~~~~~~

To run CKAN's tests using PostgreSQL as the database, you have to give the
``--with-pylons=test-core.ini`` option on the command line. This command will
run the tests for CKAN core and for the core extensions::

     nosetests --ckan --with-pylons=test-core.ini ckan ckanext

The speed of the PostgreSQL tests can be improved by running PostgreSQL in
memory and turning off durability, as described
`in the PostgreSQL documentation <http://www.postgresql.org/docs/9.0/static/non-durability.html>`_.

By default the tests will keep the database between test runs. If you wish to
drop and reinitialize the database before the run you can use the ``reset-db``
option::

     nosetests --ckan --reset-db --with-pylons=test-core.ini ckan



.. _migrationtesting:

~~~~~~~~~~~~~~~~~
Migration testing
~~~~~~~~~~~~~~~~~

If you're a CKAN developer or extension developer and your new code requires a
change to CKAN's model, you'll need to write a migration script. To ensure that
the migration script itself gets tested, you should run the tests with
the ``--ckan-migration`` option, for example::

     nosetests --ckan --ckan-migration --with-pylons=test-core.ini ckan ckanext

By default tests are run using the model defined in ``ckan/model``.
With the ``--ckan-migration`` option the tests will run using a database that
has been created by running the migration scripts in ``ckan/migration``, which
is how the database is created and upgraded in production.

.. warning ::

   A common error when wanting to run tests against a particular database is to
   change ``sqlalchemy.url`` in ``test.ini`` or ``test-core.ini``. The problem
   is that these are versioned files and people have checked in these by
   mistake, creating problems for other developers.

~~~~~~~~~~~~~~~~~~~~~
Common error messages
~~~~~~~~~~~~~~~~~~~~~

ConfigError
===========

``nose.config.ConfigError: Error reading config file 'setup.cfg': no such option 'with-pylons'``
   This error can result when you run nosetests for two reasons:

   1. Pylons nose plugin failed to run. If this is the case, then within a couple of lines of running `nosetests` you'll see this warning: `Unable to load plugin pylons` followed by an error message. Fix the error here first`.

   2. The Python module 'Pylons' is not installed into you Python environment. Confirm this with::

        python -c "import pylons"

OperationalError
================

``OperationalError: (OperationalError) no such function: plainto_tsquery ...``
   This error usually results from running a test which involves search functionality, which requires using a PostgreSQL database, but another (such as SQLite) is configured. The particular test is either missing a `@search_related` decorator or there is a mixup with the test configuration files leading to the wrong database being used.

nosetests
=========

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

SolrError
=========

``SolrError: Solr responded with an error (HTTP 404): [Reason: None]
<html><head><meta content="text/html; charset=ISO-8859-1" http-equiv="Content-Type" /><title>Error 404 NOT_FOUND</title></head><body><h2>HTTP ERROR 404</h2><p>Problem accessing /solr/ckan/select/. Reason:<pre>    NOT_FOUND</pre></p><hr /><i><small>Powered by Jetty://</small></i>``

This means your solr_url is not corresponding with your SOLR. When running tests, it is usually easiest to change your set-up to match the default solr_url in test-core.ini. Often this means switching to multi-core - see :ref:`solr-multi-core`.


---------------
Front-end tests
---------------
Front-end testing consists of both automated tests (for the JavaScript code)
and manual tests (for the complete front-end consisting of HTML, CSS and
JavaScript).

~~~~~~~~~~~~~~~~~~~~~~~~~~
Automated JavaScript tests
~~~~~~~~~~~~~~~~~~~~~~~~~~

The JS tests are written using the Mocha_ test framework and run via
PhantomJS_. First you need to install the necessary packages::

    sudo apt-get install npm nodejs-legacy
    sudo npm install -g mocha-phantomjs@3.5.0 phantomjs@~1.9.1

.. _Mocha: https://mochajs.org/
.. _PhantomJS: http://phantomjs.org//ckan

To run the tests, make sure that a test server is running::

    . /usr/lib/ckan/default/bin/activate
    paster serve test-core.ini

Once the test server is running switch to another terminal and execute the
tests::

    mocha-phantomjs http://localhost:5000/base/test/index.html

~~~~~~~~~~~~
Manual tests
~~~~~~~~~~~~
All new CKAN features should be coded so that they work in the
following browsers:

* Internet Explorer: 11, 10, 9 & 8
* Firefox: Latest + previous version
* Chrome: Latest + previous version

These browsers are determined by whatever has >= 1% share with the
latest months data from: http://data.gov.uk/data/site-usage

Install browser virtual machines
================================

In order to test in all the needed browsers you'll need access to
all the above browser versions. Firefox and Chrome should be easy
whatever platform you are on. Internet Explorer is a little trickier.
You'll need Virtual Machines.

We suggest you use https://github.com/xdissent/ievms to get your
Internet Explorer virtual machines.

Testing methodology
===================

Firstly we have a primer page. If you've touched any of the core
front-end code you'll need to check if the primer is rendering
correctly. The primer is located at:
http://localhost:5000/testing/primer

Secondly whilst writing a new feature you should endeavour to test
in at least in your core browser and an alternative browser as often
as you can.

Thirdly you should fully test all new features that have a front-end
element in all browsers before making your pull request into
CKAN master.

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Common front-end pitfalls & their fixes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Here's a few of the most common front end bugs and a list of their
fixes.

Reserved JS keywords
====================

Since IE has a stricter language definition in JS it really doesn't
like you using JS reserved keywords method names, variables, etc...
This is a good list of keywords not to use in your JavaScript:

https://developer.mozilla.org/en-US/docs/JavaScript/Reference/Reserved_Words

::

  /* These are bad */
  var a = {
    default: 1,
    delete: function() {}
  };

  /* These are good */
  var a = {
    default_value: 1,
    remove: function() {}
  };

Unclosed JS arrays / objects
============================

Internet Explorer doesn't like it's JS to have unclosed JS objects
and arrays. For example:

::

  /* These are bad */
  var a = {
    b: 'c',
  };
  var a = ['b', 'c', ];

  /* These are good */
  var a = {
    c: 'c'
  };
  var a = ['b', 'c'];
