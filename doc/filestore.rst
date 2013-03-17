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


FileStore Web Interface
=======================

Upload of files to storage is integrated directly into the the Dataset creation
and editing system with files being associated to Resources.


FileStore API
=============

The :doc:`FileStore API <filestore-api>` is CKAN's API for uploading files to
the FileStore.


DataStore Integration
=====================

It is also possible to have uploaded files (if of a suitable format) stored in
the DataStore which will then provides an API to the data. See :ref:`datastorer` for more details.

