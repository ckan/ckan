==========================
FileStore and File Uploads
==========================

CKAN allows users to upload files directly to it against a resource or images
displayed against groups and organizations.

.. versionchanged:: 2.2
   Previous versions of CKAN used to allow uploads to remote cloud hosting but
   we have simplified this to only alow local file uploads.  This is to give
   CKAN more control over the files and make access control possible.  If you
   are already using pairtree local file storage then you must keep your
   current settings, otherwise users will not be also able to download the old
   uploaded files.

-------------------------------------------
Setup File Uploads
-------------------------------------------

To setup CKAN's FileStore with local file storage:

1. Create the directory where CKAN will store uploaded files:

   .. parsed-literal::

     sudo mkdir -p |storage_path|

2. Add the following lines to your CKAN config file, after the ``[app:main]``
   line:

   .. parsed-literal::

      ckan.storage_dir = |storage_path|

3. Set the permissions of the ``storage_path``. For example if you're running
   CKAN with Apache, then Apache's user (``www-data`` on Ubuntu) must have
   read, write and execute permissions for the ``storage_path``:

   .. parsed-literal::

     sudo chown www-data |storage_path|
     sudo chmod u+rwx |storage_path|

4. Restart your web server, for example to restart Apache:

   .. parsed-literal::

      |reload_apache|


-----------------------
FileStore Web Interface
-----------------------

Upload of files to storage is integrated directly into the Dataset creation
and editing system with files being associated to Resources.

-----------------------
FileStore API
-----------------------

.. versionchanged:: 2.2
    The previous API has been depricated although should still work if you where
    using local file storage.

The api is part of the resource_create and resource_update action api
functions. You can post mutipart/form-data to the api and the key, value
pairs will treated as as if they are a json object.
The extra key ``upload`` is used to actually post the binary data.

Curl automatically puts the multipart-form-data heading when using the
``--form`` option:

   .. parsed-literal::

    curl -H'Authorization: your-api-key' 'http://yourhost/api/action/resource_create' --form upload=@filetoupload --form package_id=my_dataset

The python requests library used the files parameter and automatically sets
the multipart/form-data header too:

   .. parsed-literal::

    import requests
    requests.post('http://0.0.0.0:5000/api/action/resource_create',
                   data={"package_id":"my_dataset}",
                   headers={"X-CKAN-API-Key": "21a47217-6d7b-49c5-88f9-72ebd5a4d4bb"},
                   files=[('upload', file('/path/to/file/to/upload.csv'))])

With resource_update, if you want to override a file you just need
to set the upload field again::

    curl -H'Authorization: your-api-key' 'http://yourhost/api/action/resource_update' --form upload=@newfiletoupload --form id=resourceid

If you want to clear the upload and change it for a remote URL
there is special boolean field clear_upload to do this::

    curl -H'Authorization: your-api-key' 'http://yourhost/api/action/resource_update' --form url=http://expample.com --form clear_upload=true --form id=resourceid

It is also possible to have uploaded files (if of a suitable format) stored in
the DataStore which will then provides an API to the data. See :ref:`datapusher` for more details.

