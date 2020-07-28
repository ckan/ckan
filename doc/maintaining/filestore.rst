==========================
FileStore and file uploads
==========================

When enabled, CKAN's FileStore allows users to upload data files to CKAN
resources, and to upload logo images for groups and organizations. Users will
see an upload button when creating or updating a resource, group or
organization.

.. versionadded:: 2.2
   Uploading logo images for groups and organizations was added in CKAN 2.2.

.. versionchanged:: 2.2
   Previous versions of CKAN used to allow uploads to remote cloud hosting but
   we have simplified this to only allow local file uploads (see
   :ref:`filestore_21_to_22_migration` for details on how to migrate). This is
   to give CKAN more control over the files and make access control possible.

.. seealso::

   :doc:`datastore`

    Resource files linked-to from CKAN or uploaded to CKAN's FileStore can
    also be pushed into CKAN's DataStore, which then enables data previews and
    a data API for the resources.


------------------
Setup file uploads
------------------

To setup CKAN's FileStore with local file storage:

1. Create the directory where CKAN will store uploaded files:

   .. parsed-literal::

     sudo mkdir -p |storage_path|

2. Add the following line to your CKAN config file, after the ``[app:main]``
   line:

   .. parsed-literal::

      ckan.storage_path = |storage_path|

3. Set the permissions of your :ref:`ckan.storage_path` directory.
   For example if you're running CKAN with Nginx, then the Nginx's user
   (``www-data`` on Ubuntu) must have read, write and execute permissions for
   the :ref:`ckan.storage_path`:

   .. parsed-literal::

     sudo chown www-data |storage_path|
     sudo chmod u+rwx |storage_path|

4. Restart your web server, for example to restart uWSGI on a package install:

   .. parsed-literal::

    sudo supervisorctl restart ckan-uwsgi:*


-------------
FileStore API
-------------

.. versionchanged:: 2.2
   The FileStore API was redesigned for CKAN 2.2.
   The previous API has been deprecated.

Files can be uploaded to the FileStore using the
:py:func:`~ckan.logic.action.create.resource_create` and
:py:func:`~ckan.logic.action.update.resource_update` action API
functions. You can post multipart/form-data to the API and the key, value
pairs will be treated as if they are a JSON object.
The extra key ``upload`` is used to actually post the binary data.

For example, to create a new CKAN resource and upload a file to it using
`curl <http://curl.haxx.se/>`_:

.. parsed-literal::

 curl -H'Authorization: your-api-key' 'http://yourhost/api/action/resource_create' --form upload=@filetoupload --form package_id=my_dataset

(Curl automatically sends a ``multipart-form-data`` heading with you use the
``--form`` option.)

To create a new resource and upload a file to it using the Python library
`requests <http://python-requests.org/>`_:

.. parsed-literal::

 import requests
 requests.post('http://0.0.0.0:5000/api/action/resource_create',
               data={"package_id":"my_dataset"},
               headers={"X-CKAN-API-Key": "21a47217-6d7b-49c5-88f9-72ebd5a4d4bb"},
               files=[('upload', file('/path/to/file/to/upload.csv'))])

(Requests automatically sends a ``multipart-form-data`` heading when you use the
``files=`` parameter.)

To overwrite an uploaded file with a new version of the file, post to the
:py:func:`~ckan.logic.action.update.resource_update` action and use the
``upload`` field::

    curl -H'Authorization: your-api-key' 'http://yourhost/api/action/resource_update' --form upload=@newfiletoupload --form id=resourceid

To replace an uploaded file with a link to a file at a remote URL, use the
``clear_upload`` field::

    curl -H'Authorization: your-api-key' 'http://yourhost/api/action/resource_update' --form url=http://expample.com --form clear_upload=true --form id=resourceid


.. _filestore_21_to_22_migration:

--------------------------
Migration from 2.1 to 2.2
--------------------------

If you are using pairtree local file storage then you can keep your current settings
without issue.  The pairtree and new storage can live side by side but you are still
encouraged to migrate.  If you change your config options to the ones specified in
this doc you will need to run the migration below.

If you are running remote storage then all previous links will still be accessible
but if you want to move the remote storage documents to the local storage you will
run the migration also.

In order to migrate make sure your CKAN instance is running as the script will
request the data from the instance using APIs.  You need to run the following
on the command line to do the migration::

    ckan -c |ckan.ini| db migrate-filestore

This may take a long time especially if you have a lot of files remotely.
If the remote hosting goes down or the job is interrupted it is saved to run it again
and it will try all the unsuccessful ones again.


----------------------------------------
Custom Internet media types (MIME types)
----------------------------------------

.. versionadded:: 2.2

CKAN uses the default Python library `mimetypes`_ to detect the media type of
an uploaded file. If some particular format is not included in the ones guessed
by the ``mimetypes`` library, a default ``application/octet-stream`` value will be
returned.

Users can still register a more appropriate media type by using the ``mimetypes``
library. A good way to do so is to use the ``IConfigurer`` interface so the
custom types get registered on startup::


    import mimetypes
    import ckan.plugins as p

    class MyPlugin(p.SingletonPlugin):

        p.implements(p.IConfigurer)

        def update_config(self, config):

            mimetypes.add_type('application/json', '.geojson')

            # ...



.. _mimetypes: http://docs.python.org/2/library/mimetypes.html
