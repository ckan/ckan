==========================
FileStore and File Uploads
==========================

CKAN allows users to upload files directly to file storage either on the local
file system or to online 'cloud' storage like Amazon S3 or Google Storage. The
uploaded files will be stored in the configured location.

-------------------------------------------
Setup the FileStore with Local File Storage
-------------------------------------------

To setup CKAN's FileStore with local file storage:

1. Create the directory where CKAN will store uploaded files:

   .. parsed-literal::

     sudo mkdir -p |storage_dir|

2. Add the following lines to your CKAN config file, after the ``[app:main]``
   line:

   .. parsed-literal::

      ofs.impl = pairtree
      ofs.storage_dir = |storage_dir|

3. Set the permissions of the ``storage_dir``. For example if you're running
   CKAN with Apache, then Apache's user (``www-data`` on Ubuntu) must have
   read, write and execute permissions for the ``storage_dir``:

   .. parsed-literal::

     sudo chown www-data |storage_dir|
     sudo chmod u+rwx |storage_dir|

4. Make sure you've set :ref:`ckan.site_url` in your config file.

5. Restart your web server, for example to restart Apache:

   .. parsed-literal::

      |reload_apache|


--------------------------------------
Setup the FileStore with Cloud Storage
--------------------------------------

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


-----------------------
FileStore Web Interface
-----------------------

Upload of files to storage is integrated directly into the the Dataset creation
and editing system with files being associated to Resources.

-------------
FileStore API
-------------

CKAN's FileStore API lets you upload files to CKAN's
:doc:`FileStore <filestore>`. If you're looking for an example,
`ckanclient <https://github.com/okfn/ckanclient>`_ contains
`Python code for uploading a file to CKAN using the FileStore API <https://github.com/okfn/ckanclient/blob/master/ckanclient/__init__.py#L546>`_.


FileStore Metadata API
======================

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


FileStore Form Authentication API
=================================

Provides credentials for doing operations on storage directly from a client
(using web form style POSTs).

The API is located at::

    /api/storage/auth/form/{label}

Provide fields for a form upload to storage including authentication::

    :param label: label.
    :return: json-encoded dictionary with action parameter and fields list.


FileStore Request Authentication API
====================================

Provides credentials for doing operations on storage directly from a client.

.. warning:: This API is currently disabled and will likely be deprecated.
             Use the form authentication instead.

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

---------------------
DataStore Integration
---------------------

It is also possible to have uploaded files (if of a suitable format) stored in
the DataStore which will then provides an API to the data. See :ref:`datastorer` for more details.

