=========
DataStore
=========

The CKAN DataStore provides a database for structured storage of data together
with a powerful Web API, all seamlessly integrated into the CKAN interface and
authorization system.

Overview
========

The following short set of slides provide a brief overview and introduction to
the DataStore and the Data API.

.. raw:: html

   <iframe src="https://docs.google.com/presentation/embed?id=1UhEqvEPoL_VWO5okYiEPfZTLcLYWqtvRRmB1NBsWXY8&#038;start=false&#038;loop=false&#038;delayms=3000" frameborder="0" width="480" height="389" allowfullscreen="true" mozallowfullscreen="true" webkitallowfullscreen="true"></iframe>

Relationship to FileStore
=========================

The DataStore is distinct but complementary to the FileStore (see
:doc:`file-upload`). In contrast to the the FileStore which provides 'blob'
storage of whole files with no way to access or query parts of that file, the
DataStore is like a database in which individual data elements are accessible
and queryable. To illustrate this distinction consider storing a spreadsheet
file like a CSV or Excel document. In the FileStore this filed would be stored
directly. To access it you would download the file as a whole. By contrast, if
the spreadsheet data is stored in the DataStore one would be able to access
individual spreadsheet rows via a simple web-api as well as being able to make
queries over the spreadsheet contents.

Using the DataStore Data API
============================

The DataStore's Data API, which derives from the underlying ElasticSearch
data-table, is RESTful and JSON-based with extensive query capabilities.

Each resource in a CKAN instance has an associated DataStore 'database'.  This
database will be accessible via a web interface at::

  /api/data/{resource-id}

This interface to this data is *exactly* the same as that provided by
ElasticSearch to documents of a specific type in one of its indices.

So, for example, to see the fields in this database do::

  /api/data/{resource-id}/_mapping

To do simple search do::

  /api/data/{resource-id}/_search?q=abc

For more on searching see: http://www.elasticsearch.org/guide/reference/api/search/uri-request.html


Installation and Configuration
=============================

The DataStore uses ElasticSearch_ as the persistence and query layer with CKAN
wrapping this with a thin authorization and authentication layer.

It also requires the use of Nginx as your webserver as its XSendfile_ feature
is used to transparently hand off data requests to ElasticSeach internally.

.. _ElasticSearch: http://www.elasticsearch.org/
.. _XSendfile: http://wiki.nginx.org/XSendfile

1. Install ElasticSearch_
-------------------------

Please see the ElasticSearch_ documentation.

2. Configure Nginx
------------------

You must add to your Nginx CKAN site entry the following::

    location /elastic/ {
        internal;
        # location of elastic search
        proxy_pass http://0.0.0.0:9200/;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

.. note:: update the proxy_pass field value to point to your ElasticSearch
          instance (if it is not localhost and default port).

3. Enable datastore features in CKAN
-----------------------------------

In your config file set::

 ckan.webstore.enabled = 1


DataStorer: Automatically Add Data to the DataStore
=================================================

Often, when you upload data you will want it to be automatically added to the
DataStore. This requires some processing, to extract the data from your files
and to add it to the DataStore in the format it understands. For more
information on the architecture see http://wiki.ckan.org/Storage.

This task of automatically parsing and then adding data to the datastore is
performed by a DataStorer, a queue process that runs asynchronously and can be
triggered by uploads or other activities. The DataStorer is an extension and can
be found, along with installation instructions, at:

https://github.com/okfn/ckanext-webstorer


How It Works (Technically)
==========================

1. Request arrives at e.g. /dataset/{id}/resource/{resource-id}/data
2. CKAN checks authentication and authorization.
3. (Assuming OK) CKAN hands (internally) to ElasticSearch which handles the
   request 

   * To do this we use Nginx's Sendfile / Accel-Redirect feature. This allows
     us to hand off a user request *directly* to ElasticSearch after the
     authentication and authorization. This avoids the need to proxy the
     request and results through CKAN code.

