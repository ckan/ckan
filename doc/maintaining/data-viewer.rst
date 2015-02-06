==============================
Data preview and visualization
==============================

.. versionchanged:: 2.3

    The whole way resource previews are handled was changed on CKAN 2.3.
    Please refer to previous versions of the documentation if you are using
    an older CKAN version.

.. contents::



Overview
--------

The CKAN resource page can contain one or more views of the resource data
or file contents. These are commonly referred to as *resource views*.

.. image:: /images/views_overview.png

The main features of resource views are:

* One resource can have multiple views of the same data (for example a grid
  and some graphs for tabular data).

* Dataset editors can choose which views to show, reorder them and configure
  them individually.

* Views configuration persits on the database, so it's not lost on each page
  refresh.

* Individual views can be embedded on external sites.

Different view types are implemented via custom plugins, which can be activated
on a particular CKAN site. Once these plugins are added, instance
administrators can decide which views should be created by default if the
resource is suitable (for instance a table on resources uploaded to the
DataStore, a map for spatial data, etc.).

Whether a particular resource can be rendered by the different view plugins is
decided by the view plugins themselves. This is generally done checking the
resource format or whether its data is on the :doc:`datastore` or
not.


Managing resource views
-----------------------

Users who are allowed to edit a particular dataset can also manage the views
for its resources. To access the management interface, click on the *Manage*
button on the resource page and then on the *Views* tab. From here you can
create new views, update or delete existing ones and reorder them.


.. image:: /images/manage_views.png


The *New view* dropdown will show the available view types for this particular
resource. If the list if empty, you may need to add the relevant view plugins
to the :ref:`ckan.plugins` setting on your configuration file, eg::

    ckan.plugins = ... image_view recline_view pdf_view

Defining views to appear by default
-----------------------------------

From the management interface you can create and edit views manually, but in most
cases you will want views to be created automatically on certain resource types,
so data can be visualized straight away after uploading or linking to a file.

To do so, you define a set of view plugins that should be checked whenever a
dataset or resource is created or updated. For each of them, if the resource is
a suitable one, a view will be created.

This is configured with the :ref:`ckan.views.default_views` setting. In it you
define the view plugins that you want to be created as default::

    ckan.views.default_views = recline_view pdf_view geojson_view

This configuration does not mean that each new resource will get all of these
views by default, but that for instance if the uploaded file is a PDF file,
a PDF viewer will be created automatically and so on.


Available view plugins
----------------------

Some view plugins for common formats are included in the main CKAN repository.
These don't require further setup and can be directly added to the
:ref:`ckan.plugins` setting.

Data Explorer
+++++++++++++

View plugin: ``recline_view``

Adds a rich widget, based on the Recline_ Javascript library. It  allows
querying, filtering, graphing and mapping data. The Data Explorer is optimized
for displaying structured data hosted on the :doc:`datastore`.

The Data Explorer can also display certain formats of tabular data (CSV and
Excel files) without its contents being uploaded to the DataStore. This is
done via the DataProxy_, an external service that will parse the contents of
the file and return a response that the view widget understands. However, as
the resource must be downloaded by the DataProxy service and parsed before it
is viewed, this option is slower and less reliable than viewing data that is
in the DataStore. It also does not properly support different encodings, proper
field type detection, etc so users are strongly encouraged to host data on the
DataStore instead.

.. note:: Support for the DataProxy will be dropped on future CKAN releases

The three main panes of the Data Explorer are also available as separate views.

DataStore Grid
++++++++++++++

View plugin: ``recline_grid_view``

Displays a filterable, sortable, table view of structured data.

This plugin requires data to be in the DataStore.

DataStore Graph
+++++++++++++++

View plugin: ``recline_graph_view``

Allows to create graphs from data stored on the DataStore. You can choose the
graph type (such as lines, bars, columns, etc) and restrict the displayed data,
by filtering by a certain field value or defining an offset and the number of
rows.

This plugin requires data to be in the DataStore.

DataStore Map
+++++++++++++

View plugin: ``recline_map_view``

Shows data stored on the DataStore in an interactive map. It supports plotting
markers from a pair of latitude / longitude fields or from a field containing
a GeoJSON_ representation of the geometries. The configuration also allows to
cluster markers if there is a high density of them and to zoom automatically
to the rendered features.

This plugin requires data to be in the DataStore.

Text view
+++++++++

View plugin: ``text_view``

Displays files in XML, JSON or plain text based formats with the syntax
highlighted. The formats detected can be configured using the
:ref:`ckan.preview.xml_formats`, :ref:`ckan.preview.json_formats`
and :ref:`ckan.preview.text_formats` configuration options respectively.

If you want to display files that are hosted in a different server from your
CKAN instance (eg that haven't been uploaded to CKAN) you will need to enable
the `Resource Proxy`_ plugin.

Image view
++++++++++

View plugin: ``image_view``

If the resource format is a common image format like PNG, JPEG or GIF, it adds
an ``<img>`` tag pointing to the resource URL. You can provide an alternative
URL on the edit view form.

Web page view
+++++++++++++

View plugin: ``webpage_view``

Adds an ``<iframe>`` tag to embed the resource URL. You can provide an
alternative URL on the edit view form.

    .. warning:: Do not activate this plugin unless you trust the URL sources.
        It is not recommended to enable this view type on instances where all users
        can create datasets.

Other view plugins
++++++++++++++++++

There are many more view plugins developed by the CKAN team and others which
are hosted on separate repositories. Some examples include:

* `Dashboard`_: Allows to combine multiple views into a single dashboard.
* `PDF viewer`_: Allows to render PDF files on the resource page.
* `GeoJSON map`_: Renders GeoJSON_ files on an interactive map.
* `Choropleth map`_: Displays data on the DataStore on a choropleth map.
* `Basic charts`_: Provides alternative graph types and renderings.

If you want to add another view type to this list, edit this file by sending
a pull request on GitHub.


.. todo:: Link to the documentation for writing view plugins


.. _Recline: https://github.com/okfn/recline/
.. _DataProxy: https://github.com/okfn/dataproxy
.. _GeoJSON: http://geojson.org
.. _Dashboard: https://github.com/ckan/ckanext-dashboard
.. _Basic charts: https://github.com/ckan/ckanext-basiccharts
.. _Choropleth map: https://github.com/ckan/ckanext-mapviews
.. _PDF viewer: https://github.com/ckan/ckanext-pdfview
.. _GeoJSON map: https://github.com/ckan/ckanext-spatial


.. todo:: Sort the resource proxy section

Resource Proxy
--------------

**Configuration required:** The ``resource_proxy`` extension must be added to
``ckan.plugins`` in your CKAN configuration file.
This extension is part of CKAN and so does not need to be installed separately.

This extension must be enabled if you wish to preview resources that are on a
different domain. That means if this extension is not enabled, e.g.
PDF, or JSON files that are on ``www.example.com`` while CKAN is on
``www.ckan.org`` cannot be previewed by any extension.

Previewing is prevented by the
`same origin policy <http://en.wikipedia.org/wiki/Same_origin_policy>`_ which
prevents files from different domains (different *origins*) from being loaded
into browsers. This extension gets around the same origin policy by pretending
that all files are served from the same domain (same *origin*) that
CKAN is on (e.g. ``www.ckan.org``).

If you are writing a custom preview extension that requires resources to be
proxied, you need to replace the URL that is used to load the file. This can
be done using the function :func:`ckanext.resourceproxy.plugin.get_proxified_resource_url`.
To find out whether the resource proxy is enabled, check ``ckan.resource_proxy_enabled``
from the config. You can find a complete example in the
`CKAN source <https://github.com/ckan/ckan/blob/793c2607199f2204307c12f83925257cd8eadc5e/ckanext/jsonpreview/plugin.py>`_.


.. todo:: Writing custom view types (tutorial?)

.. todo:: CLI & migration for CKAN < 2.3
