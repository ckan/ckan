.. _stats:

===============
Stats Extension
===============

CKAN can track visits to pages of your site and display statistics with the
stats extension. This extension can show the:

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

Enabling the Stats Extension
============================

To enable the stats extensions add `stats` to `ckan.plugins` in the config
file.

Viewing the Statistics
======================

To visits the statistics, use the URL `/stats`.
