===================
Linked Data and RDF
===================

CKAN has extensive support for linked data and RDF. In particular, there is
complete and functional mapping of the CKAN dataset schema to linked data
formats.


Enabling and Configuring Linked Data Support
============================================

In CKAN <= 1.6 please install the RDF extension: https://github.com/okfn/ckanext-rdf

In CKAN >= 1.7, basic RDF support will be available directly in core.

Configuration
-------------

When using the built-in RDF support (CKAN >= 1.7) there is no configuration required.  By default requests for RDF data will return the RDF generated from the built-in 'packages/read.rdf' template, which can be overridden using the extra-templates directive.

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

An example schema might look like::

  <rdf:RDF xmlns:foaf="http://xmlns.com/foaf/0.1/" xmlns:owl="http://www.w3.org/2002/07/owl#"
    xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#"
    xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
    xmlns:dcat="http://www.w3.org/ns/dcat#"
    xmlns:dct="http://purl.org/dc/terms/">
  <dcat:Dataset rdf:about="http://127.0.0.1:5000/dataset/worldwide-shark-attacks">
    <owl:sameAs rdf:resource="urn:uuid:424bdc8c-038d-4b44-8f1d-01227e920b69"></owl:sameAs>
    <dct:description>Shark attacks worldwide</dct:description>
    <dcat:keyword>sharks</dcat:keyword>
    <dcat:keyword>worldwide</dcat:keyword>
    <foaf:homepage rdf:resource="http://127.0.0.1:5000/dataset/worldwide-shark-attacks"></foaf:homepage>
    <rdfs:label>worldwide-shark-attacks</rdfs:label>
    <dct:identifier>worldwide-shark-attacks</dct:identifier>
    <dct:title>Worldwide Shark Attacks</dct:title>
    <dcat:distribution>
        <dcat:Distribution>
            <dcat:accessURL rdf:resource="https://api.scraperwiki.com/api/1.0/datastore/sqlite?format=csv&amp;name=worldwide_shark_attacks&amp;query=select+*+from+`Europe`&amp;apikey="></dcat:accessURL>
        </dcat:Distribution>
    </dcat:distribution>
    <dcat:distribution>
        <dcat:Distribution>
            <dcat:accessURL rdf:resource="https://api.scraperwiki.com/api/1.0/datastore/sqlite?format=csv&amp;name=worldwide_shark_attacks&amp;query=select+*+from+`Australia`&amp;apikey="></dcat:accessURL>
        </dcat:Distribution>
    </dcat:distribution>
    <dct:creator>
      <rdf:Description>
        <foaf:name>Ross</foaf:name>
        <foaf:mbox rdf:resource="mailto:ross.jones@okfn.org"></foaf:mbox>
      </rdf:Description>
    </dct:creator>
    <dct:contributor>
      <rdf:Description>
        <foaf:name>Ross</foaf:name>
        <foaf:mbox rdf:resource="mailto:ross.jones@okfn.org"></foaf:mbox>
      </rdf:Description>
    </dct:contributor>
    <dct:rights rdf:resource="http://www.opendefinition.org/licenses/odc-pddl"></dct:rights>
    </dcat:Dataset>
  </rdf:RDF>
