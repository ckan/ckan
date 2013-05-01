===========
Data Viewer
===========

The CKAN resource page can contain a preview of the resource's data.
This works by either:

1. Embedding the data into the page, either directly or by loading the data
   in an iframe.
2. Using a custom widget (such as `Recline <http://okfnlabs.org/recline>`_)
   to view the data.

Generally, the decision as to which action to take is determined by the type of
resource being viewed.
In general, images will be directly embedded, unstructured or plain text
files will be loaded in an iframe, and more complex data types will need to
use a custom widget.

The data preview functionality that is provided by CKAN is described in
the following sections:

* `Viewing images and text files`_
* `Viewing structured data: the Data Explorer`_
* `Viewing JSON data`_
* `Viewing PDF documents`_
* `Embedding Previews In Other Web Pages`_

These sections list the resource formats that each extension can preview and
provide instructions for how to enable each extension.
It is also possible for developers to create new extensions that can preview
different types of resources.
For more information on this topic see
`Writing Extensions <writing-extensions.html>`_.


Viewing images and text files
-----------------------------

**Configuration required:** None.
Images and text files (that match one of the file types given below) will be
previewed automatically by default.

**Resource formats:** images, plain text (details below).

By default, the following types of resources will be embedded directly into
the resource read page:

* ``png``
* ``jpg``
* ``gif``

The types of resources that are embedded directly can be specified in the
CKAN config file. See :ref:`ckan.preview.direct` for more information.

The following types of resources will be loaded in an iframe:

* ``plain``
* ``txt``
* ``html``
* ``htm``
* ``xml``
* ``rdf+xml``
* ``owl+xml``
* ``n3``
* ``n-triples``
* ``turtle``
* ``atom``
* ``rss``

The types of resources that are loaded in an iframe can be specified in the
CKAN config file. See :ref:`ckan.preview.loadable` for more information.


Viewing structured data: the Data Explorer
------------------------------------------

.. versionadded:: 2.0
   the ``recline_preview`` extension is new in CKAN 2.0.

**Configuration required:** The ``recline_preview`` extension must be added to
``ckan.plugins`` in your CKAN configuration file.
This extension is part of CKAN and so does not need to be installed separately.

**Resource formats:** DataStore, ``csv``, ``xls``.

Structured data can be previewed using the
`Recline <http://okfnlabs.org/recline>`_ Data Explorer.
The Data Explorer provides a rich, queryable view of the data, and allows the
data to be filtered, graphed and mapped.

To be viewed, the data must either be:

1. In the CKAN `DataStore <datastore.html>`_.
   This is the recommended way to preview structured data.

Or:

2. In ``csv`` or ``xls`` format.
   In this case, CKAN will first have to try to convert the file into a more
   structured format by using the
   `Dataproxy <https://github.com/okfn/dataproxy>`_.
   This is an automatic process that does not require any additional
   configuration.
   However, as the resource must be downloaded by the Dataproxy service and
   then analysed before it is viewed, this option is generally slower and less
   reliable than viewing data that is in the DataStore.


Viewing JSON data
-----------------

**Configuration required:** The ``json_preview`` extension must be added to
``ckan.plugins`` in your CKAN configuration file. If you wish to view
external JSON resources as well, the ``resource_proxy`` extension must also
be enabled.
These extensions are part of CKAN and so do not need to be installed
separately.

**Resource formats:** ``json``, ``jsonp``.

The ``json_preview`` extension provides previews of any JSON data that has been
added to a CKAN instance
(and so are stored in the `Filestore <filestore.html>`_).
To view the data the resource format must be set to "json" or "jsonp"
(case insensitive).

To also view remote JSON resources, the ``resource_proxy`` extension must be
enabled as well
(this is required in order to get around the
`same origin policy <http://en.wikipedia.org/wiki/Same_origin_policy>`_).


Viewing PDF documents
---------------------

**Configuration required:** The ``pdf_preview`` extension must be added to
``ckan.plugins`` in your CKAN configuration file.
This extension is part of CKAN and so does not need to be installed separately.

**Resource formats:** ``pdf``, ``x-pdf``, ``acrobat``, ``vnd.pdf``.

The ``pdf_preview`` extension provides previews of any ``pdf`` documents
that have been added to a CKAN instance (and so are stored in
the `Filestore <filestore.html>`_) as well as any external ``pdf`` documents.
This extension uses Mozilla's `pdf.js <http://mozilla.github.io/pdf.js>`_ library.


Embedding Previews In Other Web Pages
-------------------------------------

.. versionchanged:: 2.0
   The URL that is used to obtain the contents of the resource preview has
   changed from ``/dataset/{name}/resource/{resource_id}/embed``
   to ``/dataset/{name}/resource/{resource_id}/preview``.

For each resource, the preview content can be viewed at
``/dataset/{dataset id}/resource/{resource id}/preview``.
The preview content can therefore be embedded in other web pages by loading
the contents of this URL in an iframe.
