===========
CKAN Design
===========

Overview
========

As a system CKAN functions as a synthesis of several different services:

.. image:: ckan-features.png
  :alt: CKAN Features

CKAN is part of a larger set of tools and services designed to enable automated
use and reuse of content and data:

.. image:: ckan-vision.png
  :alt: The Debian of Data Services Stack

Architecture
============

The key entity in CKAN is a Package. The data model for a package is pretty
much what you see on: http://www.ckan.net/package/new

This in turn is heavily based on the kind of packaging information provided for
software but with some modifications. One of our aims is to keep things simple
and as generic as possible as we have data from a lot of different domains.
Thus we've tried to keep the core metadata pretty restricted but allow for
additional info either via tags or via "extra" arbitrary key/value fields. So
very roughly:

 * unique name
 * title
 * url + download url
 * author/maintainer info
 * license
 * notes
 * tags
 * [extendable with "extra" fields]

All, the code is open-source and if you want to see the actual
model definitions in code see here (probably start with core.py):

<https://bitbucket.org/okfn/ckan/src/default/ckan/model/>

One thing to note here is that all changes to package data are versioned in a
wiki-like manner. This gives us a lot of flexibility in how we manage access to
the system (as well as providing features like change logging for free!).

The rdfizing code can be found here:

<https://bitbucket.org/okfn/ckan/src/default/ckan/lib/rdf.py>

