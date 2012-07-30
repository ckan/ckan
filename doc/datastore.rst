==========================
DataStore and the Data API
==========================

The CKAN DataStore provides a database for structured storage of data together
with a powerful Web-accesible Data API, all seamlessly integrated into the CKAN
interface and authorization system.

Overview
========

The following short set of slides provide a brief overview and introduction to
the DataStore and the Data API.

.. raw:: html

   <iframe src="https://docs.google.com/presentation/embed?id=1UhEqvEPoL_VWO5okYiEPfZTLcLYWqtvRRmB1NBsWXY8&#038;start=false&#038;loop=false&#038;delayms=3000" frameborder="0" width="480" height="389" allowfullscreen="true" mozallowfullscreen="true" webkitallowfullscreen="true"></iframe>

Relationship to FileStore
=========================

The DataStore is distinct but complementary to the FileStore (see
:doc:`filestore`). In contrast to the the FileStore which provides 'blob'
storage of whole files with no way to access or query parts of that file, the
DataStore is like a database in which individual data elements are accessible
and queryable. To illustrate this distinction consider storing a spreadsheet
file like a CSV or Excel document. In the FileStore this filed would be stored
directly. To access it you would download the file as a whole. By contrast, if
the spreadsheet data is stored in the DataStore one would be able to access
individual spreadsheet rows via a simple web-api as well as being able to make
queries over the spreadsheet contents.

The DataStore Data API
======================

The DataStore's Data API, which derives from the underlying ElasticSearch
data-table, is RESTful and JSON-based with extensive query capabilities.

Each resource in a CKAN instance has an associated DataStore 'table'. This
table will be accessible via a web interface at::

  /api/data/{resource-id}

This interface to this data is *exactly* the same as that provided by
ElasticSearch to documents of a specific type in one of its indices.

For a detailed tutorial on using this API see :doc:`using-data-api`.

Installation and Configuration
==============================

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

As previously mentioned, Nginx will be used on top of CKAN to forward
requests to Elastic Search. CKAN will still be served by Apache or the
development server (Paster), but all requests will be forwarded to it
by Ngnix.

This is an example of an Nginx configuration file. Note the two locations
defined, `/` will point to the server running CKAN (Apache or Paster), and
`/elastic/` to the Elastic Search instance::

    server {
            listen   80 default;
            server_name  localhost;

            access_log  /var/log/nginx/localhost.access.log;

            location / {
                    # location of apache or ckan under paster
                    proxy_pass   http://127.0.0.1:8080;
                    proxy_set_header Host $host;
            }
            location /elastic/ {
                    internal;
                    # location of elastic search
                    proxy_pass http://:127.0.0.1:9200/;
                    proxy_set_header Host $host;
                    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            }
    }

.. note:: update the proxy_pass field value to point to your ElasticSearch
          instance (if it is not localhost and default port).

Remember that after setting up Nginx, you need to access CKAN via its port
(80), not the Apache or Paster (5000) one, otherwise the DataStore won't work.

3. Enable datastore features in CKAN
------------------------------------

In your config file set::

 ckan.datastore.enabled = 1

.. _datastorer:

DataStorer: Automatically Add Data to the DataStore
===================================================

Often, one wants data that is added to CKAN (whether it is linked to or uploaded to the :doc:`FileStore <filestore>`) to be automatically added to the
DataStore. This requires some processing, to extract the data from your files
and to add it to the DataStore in the format the DataStore can handle.

This task of automatically parsing and then adding data to the datastore is
performed by a DataStorer, a queue process that runs asynchronously and can be
triggered by uploads or other activities. The DataStorer is an extension and can
be found, along with installation instructions, at:

https://github.com/okfn/ckanext-datastorer


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

