==========================
Harvesting remote metadata
==========================

The `ckanext-harvest`_ extension provides functionality for harvesting records
from remote CKAN instances, as well as a framework for writing custom
harvesters for different metadata sources.

.. _ckanext-harvest: https://github.com/okfn/ckanext-harvest

CKAN harvester
==============

The CKAN harvester makes really easy to pull datasets from a remote CKAN
instance to your own. It is highly customizable, allowing to define default
tags, groups, users and permissions for the created datasets. Please refer to
the documentation for more details:

https://github.com/okfn/ckanext-harvest#the-ckan-harvester


Other harvesters
================

Other extensions offer different harvesters for other metadata sources. For
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


