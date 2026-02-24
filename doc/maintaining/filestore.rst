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

.. versionchanged:: 2.12
   Add support for configurable storages. Cloud uploads are supported via
   correspoinding storage adapters, such as ``ckan:libcloud``.

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

.. note:: CKAN is shipped only with filesystem storage. Adapters for cloud
          storage are available inside `ckanext-file-keeper-cloud
          <https://github.com/ckan/ckanext-file-keeper-cloud>`_.

In CKAN, a "storage" represents a logical container for specific set of
files. Each storage is configured separately and serves a distinct purpose:

- **Resource Storage**: Handles data files uploaded to CKAN resources
- **User Storage**: Manages user avatars
- **Group Storage**: Manages logo images for organizations/groups
- **Custom Storages**: can be configured for application-specific files

Each storage operates independently with its own configuration, but they all
use the same interface. This allows different types of files to be stored in
different locations (local filesystem, cloud storage, etc.) while maintaining a
consistent API.

For example, you might configure:

- Resource files to be stored in `/var/lib/ckan/resources`
- Organization logos in `/var/lib/ckan/logos`
- Plugin assets in an S3 bucket

All these storages will be accessible through
:py:func:`~ckan.lib.files.get_storage` function and from user's perspective
they will behave identically.

CKAN uses `file-keeper`_ as an abstraction layer for low-level interaction with
the file storages. It exposes classes that provide a standard storage interface
regardless of the underlying system. As a result, saving files into the local
files ystem, a cloud provider or a database looks exactly the same from the
code perspective.

Storages are initialized during application startup and must be configured in
advance. The exact settings depend on the type of the storage, but in general they
look like this::

  ckan.files.storage.my_storage.type = ckan:fs
  ckan.files.storage.my_storage.path = /tmp/my_storage
  ckan.files.storage.my_storage.initialize = true

Any option that starts with ``ckan.files.storage.`` is a storage
configuration. After the prefix follows the name of the storage,
``my_storage``, and everything after the name is an option that will be
consumed by the storage.

In the example above, storage ``my_storage`` is detected with configuration
``{"type": "ckan:fs", "path": "/tmp/my_storage", "initialize":
true}``. Configuration for storages is grouped by the name, and that allows
multiple storages to be configured at the same time::

  ckan.files.storage.a.type = xxx
  ckan.files.storage.b.type = yyy
  ckan.files.storage.c.type = zzz

It results in three storages:

* ``a`` with configuration ``{"type": "xxx"}``
* ``b`` with configuration ``{"type": "yyy"}``
* ``c`` with configuration ``{"type": "zzz"}``

To get the instance of the storage, use the``ckan.lib.files.get_storage``
function::

  storage = get_storage("my_storage")

To create a new file in the storage use its
:py:meth:`~ckan.lib.files.Storage.upload` method and the
:py:func:`~ckan.lib.files.make_upload` function, which can transform a variety
of objects into an uploadable structure::

  upload = make_upload(b"hello world")
  info = storage.upload("file.txt", upload)

When the storage instance uploads the file, it returns an object with the file details, namely
its location, size, content type and content hash. This information is required
to read the file back from the storage::

  content = storage.content(info)

When the object with the file details is not available, it can usually be
created manually using the location of the file and the
:py:class:`~ckan.lib.files.FileData` class::

  path = "path/to/file/inside/the/storage.txt"
  info = FileData(path)
  content = storage.content(info)


Additional information about storage functionality is available in the
`file-keeper`_ documentation.


--------
File API
--------

:py:class:`~ckan.lib.files.Storage` exposes low-level methods for dealing with
files, but generally it's expected that files are managed through API. There is
a set of API actions aimed at file management and here's the list of the most
important ones:

* :py:func:`~ckan.logic.action.file.file_create`
* :py:func:`~ckan.logic.action.file.file_delete`
* :py:func:`~ckan.logic.action.file.file_show`
* :py:func:`~ckan.logic.action.file.file_ownership_transfer`

The main difference between file created directly using
:py:meth:`~ckan.lib.files.Storage.upload` and file created via
:py:func:`~ckan.logic.action.file.file_create` is that the latter is registered
in the database and has a corresponding record in the files table. This means
that file created via API is tracked by CKAN, works with permissions system,
and can be accessed using generic download URL, while file created directly via
storage is not registered in DB and can be accessed only via code if its
location is known.

API is build around safe assumptions, making it the recommended way to manage
files in CKAN. For example, there is no API method to override or modify file's
content. Once file is created via API, its content is immutable and can be
deleted, but not changed. To update the file, it must be deleted and created
again with new content. This approach allows CKAN to maintain integrity of the
files and avoid potential security issues related to file
modifications. Because every file has unique ID, if file once referenced from a
different entity (for example, a resource), there is guarantee that a content,
hash, size, and type of the file will remain the same as long as the file
exists in the system. If file gets deleted and new file will be created in the
same location, this new file will have different ID and will not be referenced
from the entities that pointed to the previous file, so there is no risk of
unintentional content change for the users of the system. For example, it means
that it's impossible to upload an image as a user avatar and then replace it
with an HTML page(known way of hacking portals without upload restrictions).

File API has built-in permission checks, so only authorized users can create,
delete or view files. By default, only sysadmin can upload files unless
:ref:`ckan.files.authenticated_uploads.allow` config option is enabled, which
grants every authenticated user with permission to upload files.

.. note:: When :ref:`ckan.files.authenticated_uploads.allow` is enabled, users
          are allowed to upload files into storages specified by
          :ref:`ckan.files.authenticated_uploads.storages`. By default this
          option is empty and must be also updated when authenticated uploads
          are enabled.

Once file is created, the user who called ``file_create`` action is set as
file's *owner*. Owner of the file is used by file permissions system, to decide
whether user is allowed to access the file or intract with it in other way. By
default, only user who owns the file and sysadmin have permissions to access
the it. But these permissions can be extended both through configuration and
plugins.

To extend permissions via configuration, use
:ref:`ckan.files.owner.cascade_access` config option. This option expects space
separated list of entities that can be assigned as a file
owner(e.g. ``resource``, ``package``, ``group``, ``something-else``) and it
allows user to perform operation with file as long as user is allowed to
perform corresponding operation with the owner of the file. For example, if
file transfered to resource using
:py:func:`~ckan.logic.action.file.file_ownership_transfer` API action, then any
user who has permission to call ``resource_show`` for the given resource is
also allowed to call ``file_show`` for the any file owned by this resource. To
be more precise, when file is ownedy by anything that has type ``XXX``, and this
``XXX`` is listed among :ref:`ckan.files.owner.cascade_access` values, then
``XXX_show`` auth function is called whenever user tries to call ``file_show``.

If file owned by ``package``, ``package_show`` is called. If file owned by
``group``, ``group_show`` is called. If file is called by ``anything_else``,
``anything_else_show`` is called. As long as corresponding auth function
exists, it will be used to decide whether user is allowed to read file's
details. If auth function does not exist, user is not allowed to read file's
details.

There are 3 types of operations that mapped in this way:

* ``show``: any action that reads file's data is mapped to ``OWNER_TYPE_show``
* ``delete``: any action that removes the file is mapped to ``OWNER_TYPE_delete``
* ``update``: any action that modifies file's data(``file_rename``,
  ``file_transfer_ownership``) is mapped to ``OWNER_TYPE_update``

And these operations cover basic usage scenarios, such as uploading file to
resource and then allowing users who can read the resource to read the file, or
allowing users who can delete the resource to delete the file, etc.

For more complex scenarios, such as preventing user who can read file's
metadata via ``file_show`` from downloading the file, custom permissions can be
implemented in plugins, by overriding auth functions.

When overriding auth functions, consider hierarchy of permissions. For example,
to override permissions of ``file_show`` action that returns file's metadata:

* override ``file_show`` auth function that is used by action directly. Or
* override ``permission_read_file`` auth function that is internally called by
  ``file_show`` and can be potentially used by other actions related to
  obtaining file's details. Or
* override ``permission_owns_file`` that is internally called by any action
  that works with existing file(accepts ``id`` of the file). Or
* override ``permission_manage_files`` that is internally called by every
  action, including ``file_create``.

Methods mentioned lower in the list have wider scope and they should be
overriden only if global modification of all corresponding permissions is
intended. The ideal solution is to override auth function with the name that
matches the name of the API action that will be affected, but there are
situations, where it's not possible. For example, file cannot be downloaded via
API, that's why downloads are controlled by ``permission_download_file``.

Here's the full hierarchy of auth functions related to files::

  permission_manage_files              # Root permission: file management
  ├─ permission_owns_file              # Actions available to file owner
  │  ├─ permission_edit_file           # Editing capabilities
  │  │  ├─ file_rename                 # Rename file
  │  │  ├─ file_pin                    # Pin file
  │  │  ├─ file_unpin                  # Unpin file
  │  │  └─ file_ownership_transfer     # Transfer ownership
  │  ├─ permission_delete_file         # Deletion rights
  │  │  └─ file_delete                 # Delete file
  │  └─ permission_read_file           # Read access
  │     ├─ permission_download_file    # Download rights
  │     └─ file_show                   # View file
  ├─ file_create                       # Create new file
  ├─ file_register                     # Register file in system
  └─ file_owner_scan                   # See all files of the given owner

--------------
Download files
--------------

While :py:class:`~ckan.lib.files.Storage` has
:py:meth:`~ckan.lib.files.Storage.stream` and
:py:meth:`~ckan.lib.files.Storage.content` methods that return file content,
it's not the only way to access files. Any file registered in DB(i.e., created
via ``file_create`` or similar API action and tracked via DB record in the
files table) can be accessed using generic download URL. To build the URL for
the file, generate a link to ``file.download`` endpoint, providing file's ID as
an ``id`` parameter of the URL::

  download_url = h.url_for("file.download", id=FILE_ID)

This endpoint performs generic access check before sending file to user. It
calls ``permission_download_file`` auth function, which can be overriden to
implement custom access rules, like restricted downloads even if user has
access to file's metadata.

.. note:: By default file is accessible only by sysadmin and user who owns the
          file. To extend download permissions, consider transfering file
          ownership to organization/package/resource via
          :py:func:`~ckan.logic.action.file.file_ownership_transfer` and then
          enable cascade access to the given owner via
          :ref:`ckan.files.owner.cascade_access`.

As an alternative, when writing custom view functions,
:py:meth:`ckan.lib.files.Storage.as_response` method can be used to create
Flask's response object with the file content. Depending on the storage
backend, it can be either a response with the actual file content, or a
redirect response to the external public file location. Such response can be
returned from the view function as is::

    @my_blueprint.route("/my/custom/download/<id>")
    def download(id: str) -> Response:
        try:
            item: dict[str, Any] = logic.get_action("file_show")({}, {"id": id})
        except logic.NotFound:
            return base.abort(404)

        file_data: FileData = files.FileData.from_dict(item)
        storage: Storage = files.get_storage(item["storage"])

        return storage.as_response(data)

-------------
Storage types
-------------

Configuring a storage requires defining its ``type`` of the storage. Apart from
the type, there is a number of common options that are supported by all storage
types.

* ``max_size``: The maximum size of a single upload
* ``supported_types``: Space-separated list of allowed MIME types
* ``override_existing``: If file already exists, replace it with new content
* ``location_transformers``: List of transformations applied to the file
  location. Transformations are not applied automatically - call
  :py:meth:`~ckan.lib.files.Storage.prepare_location` to get the transformed version
  of the filename.

The rest of options depends on the specific storage type. CKAN provides the following
built-in storage types:

ckan:fs
^^^^^^^

Example::

  ckan.files.storage.my_storage.type = ckan:fs
  ckan.files.storage.my_storage.initialize = true
  ckan.files.storage.my_storage.path = /var/lib/storage/my_storage

Keeps files inside the local filesystem. Files are uploaded into a directory
specified by the required ``path`` option. The directory must exist and be
writable by the CKAN process. If directory does not exist, it's created when
``initialize`` option is enabled. If ``initialize`` is not enabled, exception
is raised during initialization of the storage.

ckan:fs:public
^^^^^^^^^^^^^^
Example::

  ckan.files.storage.my_public_storage.type = ckan:fs:public
  ckan.files.storage.my_public_storage.initialize = true
  ckan.files.storage.my_public_storage.path = /var/lib/storage/my_public_storage

  # make storage folder available at application root
  extra_public_paths = /var/lib/storage/my_public_storage


Extended version of ``ckan:fs`` type. It assumes that ``path`` is registered as
CKAN public folder and all files from it are accessible directly from the
browser. Can be used for non-private uploads, such as user avatars or group
images. If ``path`` points to the subfolder of the public directory, i.e, CKAN
registers ``/data/storage`` as public directory, but storage's ``path`` is set
to ``/data/storage/nested/path/inside``, use ``public_prefix`` option to
specify static segment that must be added to file's location in order to build
valid public URL. In the given example, ``public_prefix`` must be set to
``nested/path/inside``.


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

   .. method:: prepare_location(location: str, sample: Upload | None = None) -> Location

      Transform and sanitize location using configured functions.

      This method applies all transformations configured in
      :py:attr:`~ckan.lib.files.Settings.location_transformers` setting to the
      provided location. Each transformer is called in the order they are
      listed in the setting. The output of the previous transformer is passed
      as an input to the next one.

      Example:

      >>> location = storage.prepare_location(untrusted_location)

      :param location: initial location provided by user
      :param sample: optional Upload object that can be used by transformers.
      :returns: transformed location

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
