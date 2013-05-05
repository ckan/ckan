==========================
FileStore and File Uploads
==========================

CKAN allows users to upload files directly to file storage either on the local
file system or to online 'cloud' storage like Amazon S3 or Google Storage. The
uploaded files will be stored in the configured location.

Setup the FileStore with Local File Storage
===========================================

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

      |restart_apache|

Setup the FileStore with Cloud Storage
======================================

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

