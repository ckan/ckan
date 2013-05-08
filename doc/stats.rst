.. _stats:

===============
Stats Extension
===============

CKAN can analyze its database and display the results with the stats extension.
This extension can show the:

* Total Number of Datasets
* Dataset Revisions per Week
* Top Rated Datasets
* Most Edited Datasets
* Largest Groups
* Top Tags
* Users Owning Most Datasets

.. seealso::

 `ckanext-googleanalytics <https://github.com/okfn/ckanext-googleanalytics>`_
    A CKAN extension that integrates Google Analytics into CKAN.

.. seealso::

  :ref:`tracking`
  CKAN can track visits to pages of your site to show and highlight popular datasets.

Enabling the Stats Extension
============================

To enable the stats extensions add ``stats`` to ``ckan.plugins`` in the config
file. If you set :ref:`ckanext.stats.cache_enabled` to `true`, CKAN will cache
the stats for one day instead of calculating them each time a user visits the
stats page.

Viewing the Statistics
======================

To visits the statistics, use the URL ``/stats``.
