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

.. seealso::

   :doc:`CKAN coding standards for tests <testing>`
     Conventions for writing tests for CKAN

--------------
Back-end tests
--------------

Most of CKAN's testsuite is for the backend Python code.

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Install additional dependencies
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Some additional dependencies are needed to run the tests. Make sure you've
created a config file at |ckan.ini|, then activate your
virtual environment:

.. parsed-literal::

    |activate|

Install pytest and other test-specific CKAN dependencies into your virtual
environment:

.. parsed-literal::

    pip install -r |virtualenv|/src/ckan/dev-requirements.txt

.. _datastore-test-set-permissions:

~~~~~~~~~~~~~~~~~~~~~~~~~
Set up the test databases
~~~~~~~~~~~~~~~~~~~~~~~~~

Create test databases:

.. parsed-literal::

    sudo -u postgres createdb -O |database_user| |test_database| -E utf-8
    sudo -u postgres createdb -O |database_user| |test_datastore| -E utf-8

Set the permissions::

    ckan -c test-core.ini datastore set-permissions | sudo -u postgres psql

When the tests run they will use these databases, because in ``test-core.ini``
they are specified in the ``sqlalchemy.url`` and ``ckan.datastore.write_url``
connection strings.

You should also make sure that the :ref:`Redis database <ckan.redis.url>`
configured in ``test-core.ini`` is different from your production database.


.. _solr-multi-core:

~~~~~~~~~~~~~~~~~~~~~~~~~
Configure Solr Multi-core
~~~~~~~~~~~~~~~~~~~~~~~~~

The tests assume that Solr is configured 'multi-core', whereas the default
Solr set-up is often 'single-core'. You can ask Solr for its cores status::

    curl -s 'http://127.0.0.1:8983/solr/admin/cores?action=STATUS' |python -c 'import sys;import xml.dom.minidom;s=sys.stdin.read();print(xml.dom.minidom.parseString(s).toprettyxml())'

Each core will be within a child from the ``<lst name="status"`` element, and contain a ``<str name="instanceDir">`` element.

You can also tell from your ckan config (assuming ckan is working)::

    grep solr_url |ckan.ini|
    # single-core: solr_url = http://127.0.0.1:8983/solr
    # multi-core:  solr_url = http://127.0.0.1:8983/solr/ckan

To enable multi-core:

1. Find the ``instanceDir`` of the existing Solr core. It is found in the output of the curl command above.

       e.g. ``/usr/share/solr/`` or ``/opt/solr/example/solr/collection1``

2. Make a copy of that core's directory e.g.::

       sudo cp -r /usr/share/solr/ /etc/solr/ckan

3. Find your solr.xml. It is in the Solr Home directory given by this command::

       curl -s 'http://127.0.0.1:8983/solr/admin/' | grep SolrHome

4. Configure Solr with the new core by editing ``solr.xml``. The 'cores' section will have one 'core' in it already and needs the second one 'ckan' added so it looks like this::

       <cores adminPath="/admin/cores" defaultCoreName="collection1">
         <core name="collection1" instanceDir="." />
         <core name="ckan" instanceDir="/etc/solr/ckan" />
       </cores>

5. Restart Solr by restarting Jetty (or Tomcat)::

       sudo service jetty restart

6. Edit your main ckan config (e.g. |ckan.ini|) and adjust the solr_url to match::

       solr_url = http://127.0.0.1:8983/solr/ckan


~~~~~~~~~~~~~
Run the tests
~~~~~~~~~~~~~

To run CKAN's tests using PostgreSQL as the database, you have to give the
``--ckan-ini=test-core.ini`` option on the command line. This command will
run the tests for CKAN core and for the core extensions::

     pytest --ckan-ini=test-core.ini ckan/ ckanext/

The speed of the PostgreSQL tests can be improved by running PostgreSQL in
memory and turning off durability, as described
`in the PostgreSQL documentation <http://www.postgresql.org/docs/9.0/static/non-durability.html>`_.


~~~~~~~~~~~~~~~~~~~~~
Common error messages
~~~~~~~~~~~~~~~~~~~~~

OperationalError
================

``OperationalError: (OperationalError) no such function: plainto_tsquery ...``
   This error usually results from running a test which involves search functionality, which requires using a PostgreSQL database, but another (such as SQLite) is configured. The particular test is either missing a `@search_related` decorator or there is a mixup with the test configuration files leading to the wrong database being used.


SolrError
=========
::

    SolrError: Solr responded with an error (HTTP 404): [Reason: None]
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

The JS tests are written using the Cypress_ test framework. First you need to install the necessary packages::

    sudo apt-get install npm nodejs-legacy
    sudo npm install

.. _Cypress: https://www.cypress.io/

To run the tests, make sure that a test server is running::

    . /usr/lib/ckan/default/bin/activate
    ckan -c |ckan.ini| run

Once the test server is running switch to another terminal and execute the
tests::

    npx cypress run

~~~~~~~~~~~~
Manual tests
~~~~~~~~~~~~
All new CKAN features should be coded so that they work in the
following browsers:

* Internet Explorer: 11, 10, 9 & 8
* Firefox: Latest + previous version
* Chrome: Latest + previous version

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
