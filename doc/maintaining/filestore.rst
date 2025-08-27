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

.. versionchanged:: 2.12 Add support of configurable storages. Cloud uploads
   are supported via correspoinding storage adapters, such as
   ``ckan:libcloud``.

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

2. Add the following lines to your CKAN config file, after the ``[app:main]``
   line:

   .. parsed-literal::

      ckan.uploads_enabled = true
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

::

   curl -H'Authorization: your-api-key' 'http://yourhost/api/action/resource_create' \
       --form upload=@filetoupload --form package_id=my_dataset

(Curl automatically sends a ``multipart-form-data`` heading with you use the
``--form`` option.)

To create a new resource and upload a file to it using the Python library
`requests <http://python-requests.org/>`_:

.. parsed-literal::

 import requests
 requests.post('http://0.0.0.0:5000/api/action/resource_create',
               data={"package_id":"my_dataset"},
               headers={"Authorization": "21a47217-6d7b-49c5-88f9-72ebd5a4d4bb"},
               files=[('upload', open('/path/to/file/to/upload.csv', 'rb'))])

(Requests automatically sends a ``multipart-form-data`` heading when you use the
``files=`` parameter.)

To overwrite an uploaded file with a new version of the file, post to the
:py:func:`~ckan.logic.action.update.resource_update` action and use the
``upload`` field::

    curl -H'Authorization: your-api-key' 'http://yourhost/api/action/resource_update' \
        --form upload=@newfiletoupload --form id=resourceid

To replace an uploaded file with a link to a file at a remote URL, use the
``clear_upload`` field::

    curl -H'Authorization: your-api-key' 'http://yourhost/api/action/resource_update' \
        --form url=http://expample.com --form clear_upload=true --form id=resourceid


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


.. _using-configured-storages:

-------------------------
Using configured storages
-------------------------

CKAN uses `file-keeper`_ as an abstraction layer for low-level interaction with
the file storages. It exposes classes that provide standard storage interface
disregarding of the type of underlying system. As result, saving files into
local filesystem, cloud or DB looks exactly the same from code perspective.

Storages are initialized during application startup and must be configured in
advance. The exact settings depend on the type of the storage, but general form
is following::

  ckan.files.storage.my_storage.type = ckan:fs
  ckan.files.storage.my_storage.path = /tmp/my_storage
  ckan.files.storage.my_storage.initialize = true

Any option that starts with ``ckan.files.storage.`` is a storage
configuration. The next segment is the name of the storage, ``my_storage``, and
everything after the name is an option that will be consumed by the storage.

In the example above, storage ``my_storage`` is detected with configuration
``{"type": "ckan:fs", "path": "/tmp/my_storage", "initialize":
true}``. Configuration for storages is grouped by the name, and that's how
multiple storages can be configured::

  ckan.files.storage.a.type = xxx
  ckan.files.storage.b.type = yyy
  ckan.files.storage.c.type = zzz

It results in three storages:

* ``a`` with configuration ``{"type": "xxx"}``
* ``b`` with configuration ``{"type": "yyy"}``
* ``c`` with configuration ``{"type": "zzz"}``

To get the instance of the storage, use ``ckan.lib.files.get_storage``
function::

  storage = get_storage("my_storage")

Create a new file in the storage using it's ``upload`` method and
``ckan.lib.files.make_upload`` function that thansforms variety of objects into
uploadable structure::

  upload = make_upload(b"hello world")
  info = storage.upload("file.txt", upload)

When storage uploads the file, it returns an object with file details, namely
its location, size, content type and content hash. This information is required
to read file back from the storage::

  content = storage.content(info)

When the object with file details is not available, usually it can be created
manually using location of the file and ``ckan.lib.files.FileData`` class::

  path = "path/to/file/inside/the/storage.txt"
  info = FileData(path)
  content = storage.content(info)


Additional information about storage functionality is available inside
`file-keeper`_ documentation.

-------------
Storage types
-------------

Storage configuration requires ``type`` of the storage. Apart from the type,
there is a number of common options that are supported by all storage types.

* ``max_size``: The maximum size of a single upload
* ``supported_types``: Space-separated list of allowed MIME types
* ``override_existing``: If file already exists, replace it with new content
* ``location_transformers``: List of transformations applied to the file
  location. Transformations are not applied automatically - call
  :py:meth:`~ckan.lib.files.Storage.prepare_location` to get the transformed version
  of the filename.

The rest of options depends on the specific storage type. Out of the box,
following storage types are available:


ckan:fs
^^^^^^^

Keeps files inside the local filesystem. Files are uploaded into a directory
specified by the required ``path`` option. The directory must exist and be
writable by the CKAN process. If directory does not exist, it's created when
``initialize`` option is enabled. If ``initialize`` is not enabled, exception
is raised during initialization of the storage.

ckan:fs:public
^^^^^^^^^^^^^^

Extended version of ``ckan:fs`` type. It assumes that ``path`` is registered as
CKAN public folder and all files from it are accessible directly from the
browser. Can be used for non-private uploads, such as user avatars or group
images. If ``path`` points to the subfolder of the public directory, i.e, CKAN
registers ``/data/storage`` as public directory, but storage's ``path`` is set
to ``/data/storage/nested/path/inside``, use ``public_prefix`` option to
specify static segment that must be added to file's location in order to build
valid public URL. In the given example, ``public_prefix`` must be set to
``nested/path/inside``.

ckan:libcloud
^^^^^^^^^^^^^

Keeps files inside the cloud using `Apache Libcloud`_. Requires
`apache-libcloud <https://pypi.org/project/apache-libcloud/>`_ library and is
not available when this library is missing. Requires following options:

* ``provider``: one of `Apache Libcloud providers`_
* ``key``: API key or username
* ``secret``: Secret password
* ``container_name``: Name of the container/bucket

Majority of providers do not support permanent links out of the box. But if the
container supports public anonymous access and all files are available at URL
``https://<PROVIDER>/<CONTAINER>/<FILENAME>``, this shared
``https://<PROVIDER>/<CONTAINER>`` part can be specified as ``public_prefix``
of the storage. In this case, CKAN will append file's location to the
configured ``public_prefix`` whenever it needs a permanent public link for the
file.

Files are uploaded to the root of container. To specify nested location for all
uploads, use ``path`` option.

Any other provider specific option can be added inside ``params`` option which
expects a valid JSON object

ckan:s3
^^^^^^^

Keeps files inside AWS S3 bucket.

Only ``bucket`` option is required as all other parameters can be read from
environment variables. But it's recommended to set all the options through CKAN
config file:

* ``bucket``: name of the storage bucket
* ``key``: the AWS Access Key
* ``secret``: the AWS Secret Key
* ``region``:  the AWS Region of the bucket


ckan:azure_blob
^^^^^^^^^^^^^^^

Keeps files inside Microsoft Azure Blob Storage.

Recommended options:

* ``container_name``: name of the storage container
* ``account_name``: name of the Azure account
* ``account_name``: key for the Azure account


ckan:gcs
^^^^^^^^

Keeps files inside Google Cloud Storage.

Recommended options:

* ``bucket_name``: name of the storage bucket
* ``credentials_files``: path to the JSON with cloud credentials
* ``project_id``: the project which the client acts on behalf of


.. _mimetypes: https://docs.python.org/3/library/mimetypes.html
.. _file-keeper: https://pypi.org/project/file-keeper/
.. _Apache Libcloud: https://libcloud.apache.org/
.. _Apache Libcloud providers: https://libcloud.readthedocs.io/en/stable/storage/supported_providers.html#provider-matrix

-----------------
Storage utilities
-----------------

.. autofunction:: ckan.lib.files.get_storage
.. autoattribute:: ckan.lib.files.make_upload(value: Any) -> Upload

   Convert value into Upload object.

   Works with binary objects, ``io.BytesIO``, file-objects, and file-fields
   from submitted forms.

   Use this function for simple and reliable initialization of Upload
   object. Avoid creating Upload manually, unless you are 100% sure you can
   provide correct MIMEtype, size and stream.

   >>> upload = make_upload(b"hello world")
   >>> file_data = storage.upload("file.txt", upload)

   :param value: content of the file
   :returns: upload object with specified content
   :raises TypeError: content has unsupported type

.. autoclass:: ckan.lib.files.Storage
   :members:
   :exclude-members: SettingsFactory, UploaderFactory, ReaderFactory, ManagerFactory, capabilities

   .. autoattribute:: capabilities
      :no-value:
      :no-index:

   .. automethod:: prepare_location


.. autoclass:: ckan.lib.files.Settings
.. autoclass:: ckan.lib.files.Uploader
.. autoclass:: ckan.lib.files.Reader
.. autoclass:: ckan.lib.files.Manager

.. autoattribute:: ckan.lib.files.Upload

   Standard upload details produced by :py:func:`make_upload`.

   .. autoattribute:: ckan.lib.files.Upload.stream
   .. autoattribute:: ckan.lib.files.Upload.filename
   .. autoattribute:: ckan.lib.files.Upload.size
   .. autoattribute:: ckan.lib.files.Upload.content_type


.. autoattribute:: ckan.lib.files.FileData

   Information required by storage to operate the file.

   >>> info = FileData("local/path.txt", 123, "text/plain", md5_of_content)

   Location of the file usually requires sanitization and as a reminder about
   this step, typechecker produces warning whenever plain string is passed to
   the :py:class:`FileData`. The proper way of initializing file data is
   using already sanitized path wrapped into :py:class:`Location`.

   >>> safe_path = Location("sanitized/local/path.txt")
   >>> info = FileData(location)

   Logic of the process is not changed when :py:class:`Location` comes into a
   play, because it's a mere alias for ``str`` class. This flow exists to help
   detecting security issues. If any value can be safely used as a location(for
   example, file is kept in DB and location will be sanitized during execution
   of SQL statement), typechecker warnings can be ignored.

   As sanitization rules depend on storage, the recommended way to sanitize the
   location is to configure :py:attr:`Settings.location_transformers` and apply
   them to path by calling :py:meth:`~ckan.lib.files.Storage.prepare_location`.

   >>> unsafe_path = "local/path.txt"
   >>> safe_path = storage.prepare_location(unsafe_path)

   :param location: filepath, filename or any other type of unique identifier
   :param size: size of the file in bytes
   :param content_type: MIMEtype of the file
   :param hash: checksum of the file
   :param storage_data: additional details set by storage adapter

.. autoattribute:: ckan.lib.files.Capability

   Enumeration of operations supported by the storage.

   >>> read_and_write = Capability.STREAM | Capability.CREATE
   >>> if storage.supports(read_and_write)
   >>>     ...

.. autoattribute:: ckan.lib.files.Location

   Alias of ``str`` that represents sanitized location of the file
