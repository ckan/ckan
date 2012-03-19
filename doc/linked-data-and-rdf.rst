===================
Linked Data and RDF
===================

CKAN has extensive support for linked data and RDF. In particular, there is
complete and functional mapping of the CKAN dataset schema to linked data
formats.


Enabling and Configuring Linked Data Support
============================================

In CKAN <= 1.6 please install the RDF extension: https://github.com/okfn/ckanext-rdf

In CKAN >= 1.6.1, basic RDF support will be available directly in core.

Configuration
-------------

When using the built-in RDF support (CKAN >= 1.6.1) there is no configuration required.  By default requests for RDF data will return the RDF generated from the built-in 'packages/read.rdf' template, which can be overridden using the extra-templates directive.

Accessing Linked Data
=====================

To access linked data versions just access the :doc:`api` in the usual way but
set the Accept header to the format you would like to be returned. For
example::

 curl -L -H "Accept: application/rdf+xml" http://thedatahub.org/dataset/gold-prices
 curl -L -H "Accept: text/n3" http://thedatahub.org/dataset/gold-prices

An alternative method of retrieving the data is to add .rdf to the name of the dataset to download::

 curl -L http://thedatahub.org/dataset/gold-prices.rdf
 curl -L http://thedatahub.org/dataset/gold-prices.n3


Schema Mapping
==============

There are various vocabularies that can be used for describing datasets:

* Dublin core: these are the most well-known and basic. Dublin core terms includes the class *dct:Dataset*.
* DCAT_ - vocabulary for catalogues of datasets
* VoID_ - vocabulary of interlinked datasets. Specifically designed for describing *rdf* datasets. Perfect except for the fact that it is focused on RDF
* SCOVO_: this is more oriented to statistical datasets but has a *scovo:Dataset* class.

At the present CKAN uses mostly DCAT and Dublin Core.

.. _DCAT: http://vocab.deri.ie/dcat
.. _VoID: http://rdfs.org/ns/void
.. _SCOVO: http://sw.joanneum.at/scovo/schema.html

.. todo:: put in an example of converted data to illustrate the schema

