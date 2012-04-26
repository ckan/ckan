===========
Data Viewer
===========

CKAN's resource page can provide a preview of the resource's data if it is of
an appropriate format.  If the data is available through the CKAN `DataStore
<datastore.html>`_ API, or if the data is a ``csv`` or ``xls`` file; then `Recline's
<http://github.com/okfn/recline>`_ `Data Explorer`_ is used.  If the data is
another webpage; a google doc; or an image; then it is embedded in an iframe
for viewing.  Or if the data is text-like, then it's raw contents are
displayed.

Data Explorer
=============

The `Recline <http://github.com/okfn/recline>`_
Data Explorer provides a rich, queryable view of the data.  The data can be filtered,
faceted, graphed and mapped.  Furthermore, the grid, graph or map can then be
embedded into your own site using the **Embed** button, and copying the provided
html snippet into your webpage.

How It Works (Technically)
==========================

The relevant code for setting up the data viewer is found in ``application.js``.

All resources available through the `DataStore <datastore.html>`_ API are
available for viewing through the `Data Explorer`_.  using recline's
``elasticsearch`` backend.  If the datastore is not available, and the filetype
is normalized to ``csv`` or ``xls``, then a dataproxy is used to attempt to view
the data (using recline's ``dataproxy`` backend).

Embedding
---------

If a resource is viewable through the Data Explorer, then it is also embeddable
in third-party web pages.  ``/dataset/{name}/resource/{resource_id}/embed``
provides a stripped-down page containing the data explorer.  The data
explorer's state is passed through using the url's query parameters.

