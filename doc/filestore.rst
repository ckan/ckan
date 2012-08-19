==========================
FileStore and File Uploads
==========================

CKAN allows users to upload files directly to file storage either on the local
file system or to online 'cloud' storage like Amazon S3 or Google Storage. The
uploaded files will be stored in the configured location.

Setup and Configuration
=======================

By default storage is disabled. To enable it, all you need to do is configure
where files will be stored. Add the following lines afer the ``[app:main]``
line in your CKAN config file::

   ## Required
   ## 'Bucket' (subdirectory for file based storage) to use for file storage
   ckan.storage.bucket = my-bucket-name

   ## Optional
   ## maximum content size for uploads in bytes, defaults to 1Gb
   # ckanext.storage.max_content_length = 1000000000

Local File Storage
------------------

Important: you must install pairtree library for local storage to function::
          
    pip install pairtree

To enable local file storage add the following lines to your CKAN config file,
after the ``[app:main]`` line::

   ## OFS configuration
   ofs.impl = pairtree
   # directory on disk for data storage (should be empty)
   ofs.storage_dir = /my/path/to/storage/root/directory

You must also set ``ckan.site_url`` to your CKAN instance's base URL, e.g.
``http://scotdata.ckan.net``.

Cloud Storage
-------------

Important: you must install boto library for cloud storage to function::
          
    pip install boto

In your config for google::

   ## OFS configuration
   ofs.impl = google
   ofs.gs_access_key_id = GOOG....
   ofs.gs_secret_access_key = ....

For S3::

   ## OFS configuration
   ofs.impl = s3
   ofs.aws_access_key_id = ....
   ofs.aws_secret_access_key = ....


Storage Web Interface
=====================

Upload of files to storage is integrated directly into the the Dataset creation
and editing system with files being associated to Resources.


Storage API
===========

Metadata API
------------

The API is located at::

     /api/storage/metadata/{label}

It supports the following methods:

  * GET will return the metadata
  * POST will add/update metadata
  * PUT will replace metadata

Metadata is a json dict of key values which for POST and PUT should be send in body of request.

A standard response looks like::

    {
      "_bucket": "ckannet-storage",
      _content_length: 1074
      _format: "text/plain"
      _label: "/file/8630a664-0ae4-485f-99c2-126dae95653a"
      _last_modified: "Fri, 29 Apr 2011 19:27:31 GMT"
      _location: "some-location"
      _owner: null
      uploaded-by: "bff737ef-b84c-4519-914c-b4285144d8e6"
    }

Note that values with '_' are standard OFS metadata and are mostly read-only -- _format i.e. content-type can be set).


Form Authentication
-------------------

Provides credentials for doing operations on storage directly from a client
(using web form style POSTs).

The API is located at::

    /api/storage/auth/form/{label}

Provide fields for a form upload to storage including authentication::

    :param label: label.
    :return: json-encoded dictionary with action parameter and fields list.


Request Authentication API
--------------------------

Provides credentials for doing operations on storage directly from a client.

.. warning:: this API is currently disabled and will likely be deprecated. Use the
             form authentication instead.

The API is at::

    /api/storage/auth/request/{label}

Provide authentication information for a request so a client can
interact with backend storage directly::

    :param label: label.
    :param kwargs: sent either via query string for GET or json-encoded
        dict for POST). Interpreted as http headers for request plus an
        (optional) method parameter (being the HTTP method).

        Examples of headers are:

            Content-Type
            Content-Encoding (optional)
            Content-Length
            Content-MD5
            Expect (should be '100-Continue')

    :return: is a json hash containing various attributes including a
    headers dictionary containing an Authorization field which is good for
    15m.


DataStore Integration
=====================

It is also possible to have uploaded files (if of a suitable format) stored in
the DataStore which will then provides an API to the data. See :ref:`datastorer` for more details.

