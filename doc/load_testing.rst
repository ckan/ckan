=================
Load Testing CKAN
=================

What we did
===========

1. Put db in some standard state and start server::

    paster db clean && paster db create && paster create-test-data search
    # alternatively we could use a dump of the live db
    # psql -h localhost --user tester ckantest < ....

    # may want to create a production config
    paster serve development.ini

2. Do tests::

    # 5 results for this query
    ab -n 100 -c 10 -e myresults.csv "http://localhost:5000/api/search/package?q=government&all_fields=1"
    # remote test host
    # ab -n 100 -c 10 -e myresults.csv "http://test.ckan.net/api/search/package?q=geo&all_fields=1"

3. Examine results, fix, and repeat!


Research
========

Testing Tools
+++++++++++++

Apache Benchmarking Tool
------------------------

  * http://httpd.apache.org/docs/2.0/programs/ab.html
  * Well known and standard.
  * Can run against local or remote but local preferred
  * ab -n 100 -c 10 -e myresults.csv http://www.okfn.org/

funkload
--------

  * Mature and python based
  * http://funkload.nuxeo.org/
  * Functional testing primarily but with load testing support

Individual scripts
------------------

  * http://code.google.com/appengine/articles/load_test.html


High Performance Servers and Caching Utilities
----------------------------------------------

memcached
+++++++++

  * http://memcached.org/
  * In memory caching with access via a port
  * Very heavily used

Tornado
+++++++

  * http://www.tornadoweb.org/
  * Built by friendfeed and open-sourced
  * Asynchronous

