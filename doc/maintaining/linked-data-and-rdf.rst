===================
Linked Data and RDF
===================

Linked data and RDF features for CKAN are provided by the ckanext-dcat extension:

https://github.com/ckan/ckanext-dcat

These features include the RDF serializations of CKAN datasets based on `DCAT`_, that used to be generated
using templates hosted on the main CKAN repo, eg:

* https://demo.ckan.org/dataset/newcastle-city-council-payments-over-500.xml
* https://demo.ckan.org/dataset/newcastle-city-council-payments-over-500.ttl
* https://demo.ckan.org/dataset/newcastle-city-council-payments-over-500.n3
* https://demo.ckan.org/dataset/newcastle-city-council-payments-over-500.jsonld

ckanext-dcat offers many more `features <https://github.com/ckan/ckanext-dcat#overview>`_,
including catalog-wide endpoints and harvesters to import RDF data into CKAN. Please check
its documentation to know more about

As of CKAN 2.5, the RDF templates have been moved out of CKAN core in favour of the ckanext-dcat
customizable `endpoints`_. Note that previous CKAN versions can still use the ckanext-dcat
RDF representations, which will override the old ones served by CKAN core.

.. _DCAT: http://www.w3.org/TR/vocab-dcat/
.. _endpoints: https://github.com/ckan/ckanext-dcat#rdf-dcat-endpoints
