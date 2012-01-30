============
File uploads
============

CKAN allows users to upload files directly to file storage on the CKAN server. The uploaded files will be stored in the configured location.

The important settings for the CKAN .ini file are

::

    ckan.storage.bucket = ckan 
    ckan.storage.directory = /data/uploads/

(See :doc:`configuration`)

The directory where files will be stored should exist or be created before the system is used.

It is also possible to have uploaded CSV and Excel files stored in the Webstore which provides a structured data store built on a relational database backend.  The configuration of this process is described at `the CKAN wiki <http://wiki.ckan.org/Integrating_CKAN_With_Webstore>`_.

Storing data in the webstore allows for the direct retrieval of the data in a tabular format.  It is possible to fetch a single row of the data, all of the data and have it returned in HTML, CSV or JSON format. More information and the API documentation for the webstore is available in the `Webstore Documentation <http://webstore.readthedocs.org/en/latest/index.html>`_.