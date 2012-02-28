========
Webstore
========

Webstore is a structured data store integrated into CKAN. It uses ElasticSearch_
as the persistence and query layer with CKAN wrapping this with a thin
authorization and authentication layer.

To use you will need to be using Nginx as your webserver as we utilize its
XSendfile_ feature to transparently hand off data requests to ElasticSeach
internally.

.. _ElasticSearch: http://www.elasticsearch.org/
.. _XSendfile: http://wiki.nginx.org/XSendfile

Using the Webstore
==================

Each resource in a CKAN instance will now have a Webstore 'database' associated
with it. This database will be accessible via a web interface at::

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

3. Enable webstore features in CKAN
-----------------------------------

In your config file set::

 ckan.webstore.enabled = 1

4. Test it
----------



Webstorer: Automatically Add Data to the Webstore
=================================================

Often, when you upload data you will want it to be automatically added to the
Webstore. This requires some processing, to extract the data from your files
and to add it to the Webstore in the format it understands. For more
information on the architecture see http://wiki.ckan.org/Storage.

This task of automatically parsing and then adding data to the webstore is
performed by a Webstorer, a queue process that runs asynchronously and can be
triggered by uploads or other activities. The Webstorer is an extension and can
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

