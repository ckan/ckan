=======================
Geospatial Capabilities
=======================

This page documents the Geospatial features available in CKAN and how to add
geographic information to your datasets.

Metadata Conventions
====================

Over time some conventions have emerged regarding storing geospatial information on datasets:
 
* spatial-text: Textual representation of the extent / location of the package
* spatial: [http://geojson.org GeoJSON_] representation of the extent of the package (Polygon or Point)
* spatial-uri: Linked Data URI representing the place name

For example:

* spatial-text: United Kingdom 
* spatial: { "type": "Polygon",  "coordinates": [ [ [0.50, 49.74],[0.5, 59.25], [-6.88, 59.25], [-6.88, 49.74], [0.50, 49.74] ] ] } 
* spatial-uri: http://www.geonames.org/2635167  

or:

* spatial-text: Matsushima
* spatial: { "type": "Point",  "coordinates": [ 38.36, 141.07] }
* spatial-uri: http://www.geonames.org/2111964

Use of these conventions when storing information in CKAN means that your
material will easily integrate with any extensions or functionality built into
CKAN, like for instance the automatic geo-indexing of your package (see below).

Geo-enabling your datasets
==========================

To be able to use the geospatial capabilities of CKAN, you need to enable the
*spatial_query* plugin of the `Geospatial Extension`_ (Check the README for
requirements and installation).

.. _Geospatial Extension: http://github.com/okfn/ckanext-spatial

This extension adds support for geographic extents for datasets, creating a
package_extent table that stores the provided in a geometry type column
(PostGIS_ is used as the backend and GeoAlchemy_ as the spatial library). CKAN
supports different projections when creating this table, but it is recommended
to use the default one (WGS 84 Latitude / Longitude - EPSG:4326).

.. _PostGIS: http://www.postgis.org
.. _GeoAlchemy: http://geoalchemy.org

In order to get a dataset geometry imported into this table, an special extra
must be defined, with its key named **spatial** (above). The value of this
extra must be a valid GeoJSON_ geometry, for example::

 {"type":"Polygon","coordinates":[[[2.05827, 49.8625],[2.05827, 55.7447], [-6.41736, 55.7447], [-6.41736, 49.8625], [2.05827, 49.8625]]]}

Or::

  { "type": "Point", "coordinates": [-3.145,53.078] }

.. _GeoJSON: http://geojson.org 

Every time a dataset is created, updated or deleted, the extension will
synchronize the information stored in this extra with the geometry table.


Spatial Query
-------------

The *spatial_query* plugin in the `Geospatial Extension`_ adds support for
bounding box queries on the search API::

  /api/2/search/package/geo?bbox=xmin,ymin,xmax,ymax
  /api/2/search/package/geo?bbox=west,south,east,north

For instance::

  /api/2/search/package/geo?bbox=-3.224605,53.950255,-3.024175,54.129025

Coordinates can be provided in a different projection system, if the spatial
reference id is provided::

  api/2/search/package/geo?bbox=320073,450947,332882,471045&crs=epsg:27700

These requests will return the usual search API output::

  {
   "count": 2, 
   "results": ["bb22bf62-6816-4b5f-97ea-ca8e8a4ce60c", "5016d4fe-acd8-42f7-bb7a-e0fb50a5e1fc"]
  }

Right now only bounding box searches are supported, but support for other types
of search, as well as integration with the web frontend is planned.

Dataset Extent Map
------------------

If you want to show a small map showing the geographic coverage of your dataset
you need to enable the *spatial_query* and *dataset_extent_map* plugins of the
`Geospatial Extension`_ (Check the README for requirements and installation).

After enabling the plugin, if datasets contain a 'spatial' extra like the one
described in the previous section, a map will be shown on the dataset details
page.

.. image:: http://farm8.staticflickr.com/7089/7072071969_9061f874b4_z.jpg

The map is built using OpenLayers_ and shows cartography from the OpenStreetMap_.

.. _OpenLayers: http://openlayers.org
.. _OpenStreetMap: http://openstreetmap.org

*Note*: Right now only geometries defined in WGS 84 Latitude / Longitude
(EPSG:4326) projection are supported (e.g. the ones shown as example in this
document).

Previewing geospatial resources
===============================

WMS Previewing
--------------

To use it, enable the *wms_preview* plugin of the `Geospatial Extension`_.

.. warning:: The WMS viewer is still experimental.

The WMS (Web Map Service) previewing extension adds a light WMS client that
allows to preview the different layers.  When installed, if the package has a
resource with format *WMS* it will show a *View available WMS layer* link in
the 'Resources' section. Clicking on it will open a light map viewer with a map
list of available layers:

.. image:: http://farm6.staticflickr.com/5111/6926001238_d2f0299eca_z.jpg


Developer Notes
===============

The WMS viewer is built with OpenLayers_. There are various proposed
improvements:

* Base layer (we would need to handle different projections)
* Show legends (WMS GetLegendGraphic)
* Query layers (WMS GetFeatureInfo)
* Support other layer types (KML, GeoJson...)

