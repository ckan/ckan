========================================
Import ("Harvest") Data from Other Sites
========================================

The `ckanext-harvest`_ extension can automatically import ("harvest") datasets
from multiple CKAN websites into a single CKAN website, and also provides a
framework for writing custom harvesters to import data from non-CKAN sources.

.. _ckanext-harvest: https://github.com/okfn/ckanext-harvest

CKAN harvester
==============

The CKAN harvester plugin makes it really easy to import datasets from a remote
CKAN instance into your own CKAN instance. It is highly customizable, allowing
you to define default tags, groups, users and permissions for the imported
datasets.  Please refer to the documentation for more details:

https://github.com/okfn/ckanext-harvest#the-ckan-harvester


Other harvesters
================

There are other extensions offer different harvesters for other metadata sources. For
instance, `ckanext-inspire`_ provides harvesters for CSW records that follow
the ISO-19193 encoding.

See :ref:`csw_support` for more details.

.. _ckanext-inspire: https://github.com/okfn/ckanext-inspire


Build your own
==============

The harvesting extension provides an interface for building custom harvesters.
The interface has three stages:

1. The *gather* stage compiles all the resource identifiers that need to be fetched in the next stage.
2. The *fetch* stage gets the contents of the remote objects and stores them in the database.
3. The *import* stage performs any necessary actions on the fetched resource.

See the following section in the ckanext-harvest README for more details:

https://github.com/okfn/ckanext-harvest#the-harvesting-interface

The CKAN harvester itself uses this interface:

https://github.com/okfn/ckanext-harvest/blob/master/ckanext/harvest/harvesters/ckanharvester.py

Here you can also find other examples of custom harvesters:

https://github.com/okfn/ckanext-pdeu/tree/master/ckanext/pdeu/harvesters


