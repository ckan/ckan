=======================
Geospatial Capabilities
=======================

CKAN offers a powerful set of geospatial features that allow adding spatial
information to your datasets.

Spatial metadata for datasets
=============================

All the features in this section are provided by the `ckanext-spatial`_
extension (check the README for requirements and installation).

.. _ckanext-spatial: http://github.com/okfn/ckanext-spatial

* Associate geographic data with datasets, with automatic geo-indexing of
  datasets (**spatial_metadata** plugin)

  When activated, this plugin allows users to associate a geometry with a CKAN
  dataset, by adding a `GeoJSON`_ extra value to the dataset with key
  **spatial**. For example::

     {"type":"Polygon","coordinates":[[[2.05827, 49.8625],[2.05827, 55.7447], [-6.41736, 55.7447], [-6.41736, 49.8625], [2.05827, 49.8625]]]}

  Or::

     { "type": "Point", "coordinates": [-3.145,53.078] }

  Datasets with spatial values are automatically geo-indexed, for example so
  that they can be searched using spatial filters.

  The spatial model requires the installation and configuration of PostGIS on
  your database backend, as described on the `installation instructions`_.

.. _GeoJSON: http://geojson.org
.. _installation instructions: https://github.com/okfn/ckanext-spatial#setting-up-postgis

* Search for datasets using spatial queries (**spatial_query** plugin)

  Once your datasets are geo-indexed, you can perform spatial queries by
  bounding box, via the following API call::

      /api/2/search/dataset/geo?bbox={minx,miny,maxx,maxy}[&crs={srid}]

  Or, starting on CKAN 1.6, as part of the default search::

    POST http://localhost:5000/api/action/package_search
    {
        "q": "Pollution",
        "extras": {
            "ext_bbox": "-7.535093,49.208494,3.890688,57.372349"
        }
    }

  Check the documentation on the ckanext-spatial README for more details:

  https://github.com/okfn/ckanext-spatial#spatial-query

* Add a map widget for spatial search queries (**spatial_query_widget** plugin)

  You can display a small map widget on the dataset search form, users can draw
  a rectangle on the map to add a spatial filter to their search queries.

  Check the documentation on the ckanext-spatial README for more details:

  https://github.com/okfn/ckanext-spatial#spatial-query-widget

.. image:: http://i.imgur.com/WoEwR.png


* Add map widgets to datasets (**dataset_extent_map** plugin)

  You can add map widgets to dataset pages, to show the geometric extents of
  the datasets. Check the documentation in the ckanext-spatial README for more
  details:

  https://github.com/okfn/ckanext-spatial#dataset-extent-map

.. image:: http://i.imgur.com/GYggu.png


Metadata Conventions
====================

Over time some conventions have emerged for storing geospatial information as
extra metadata fields in datasets. Follow these conventions when storing
information in CKAN datasets, so that your datasets will easily integrate with
CKAN extensions and built-in functions, such as the automatic geo-indexing of
datasets. The following metadata keys are used:

* spatial-text: Textual representation of the extent / location of the package
* spatial: `GeoJSON`_ representation of the extent of the package (Polygon or Point)
* spatial-uri: Linked Data URI representing the place name

For example::

    * spatial-text: United Kingdom
    * spatial: {"type": "Polygon", "coordinates": [[[0.50, 49.74], [0.5, 59.25], [-6.88, 59.25], [-6.88, 49.74], [0.50, 49.74]]]}
    * spatial-uri: http://www.geonames.org/2635167

or::

    * spatial-text: Matsushima
    * spatial: {"type": "Point", "coordinates": [38.36, 141.07]}
    * spatial-uri: http://www.geonames.org/2111964


.. _GeoJSON: http://geojson.org


.. _csw_support:

CSW support
===========

CKAN offers support for the Catalogue Service for the Web (CSW) standard. This
support consist of:

* Ability to harvest records from remote CSW servers (as well as individual
  documents available online or Web Accessible Folders of them). CKAN supports
  the ISO-19139 encoding.

* Basic CSW interface (for the harvested records)

This is done via different extensions: `ckanext-harvest`_ (See :doc:`harvesting`)
offers the harvesting infrastucture, `ckanext-inspire`_ implements the
harvesters for CSW servers and `ckanext-csw`_ is required by the previous one
and offers the CSW interface.

Please refer to the README files of these extensions for instructions on how to
install and configure them.

.. _ckanext-harvest: https://github.com/okfn/ckanext-harvest
.. _ckanext-inspire: https://github.com/okfn/ckanext-inspire
.. _ckanext-csw: https://github.com/okfn/ckanext-csw


