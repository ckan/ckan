.. _stats:

===============
Stats Extension
===============

CKAN's stats extension analyzes your CKAN database and displays several tables
and graphs with statistics about your site, including:

* Total number of datasets
* Dataset revisions per week
* Top-rated datasets
* Most-edited Datasets
* Largest groups
* Top tags
* Users owning most datasets

.. seealso::

  CKAN's :ref:`built-in page view tracking feature <tracking>`, which tracks
  visits to pages.

.. seealso::

 `ckanext-googleanalytics <https://github.com/ckan/ckanext-googleanalytics>`_
    A CKAN extension that integrates Google Analytics into CKAN.


Enabling the Stats Extension
============================

To enable the stats extensions add ``stats`` to the :ref:`ckan.plugins` option
in your CKAN config file, for example::

  ckan.plugins = stats

If you also set the :ref:`ckanext.stats.cache_enabled` option to ``true``, CKAN
will cache the stats for one day instead of calculating them each time a user
visits the stats page.

Viewing the Statistics
======================

To view the statistics reported by the stats extension, visit the ``/stats``
page, for example: http://demo.ckan.org/stats
