Added support of file storages: :ref:`using-configured-storages`.

When either ``default`` storage, or individual storages for resource, group,
user and admin uploads are configured, :py:class:`~ckan.lib.uploader.Upload`
and :py:class:`~ckan.lib.uploader.ResourceUpload` are replaced by
:py:class:`~ckan.lib.uploader.FKUpload` and
:py:class:`~ckan.lib.uploader.FKResourceUpload`. These new classes use
configurable storages and serve the role of the bridge between classic file
management system in CKAN and the new one.

New classes resemble original versions with certain attributes unified under a
new ``storage`` attribute:

* ``storage_path``: available as ``upload.storage.settings.path``
* ``filepath``: can be built by joining ``path`` from storage's settings and ``upload.filename``
* ``old_filepath``: can be built by joining ``path`` from storage's settings and ``upload.old_filename``

``upload_file`` attribute contains :py:class:`ckan.lib.files.Upload` instead of
werkzeug's ``FileStorage``.

Helper :py:func:`~ckan.lib.helpers.uploads_enabled` now requires the type of
upload to check if uploads are enabled for that type.

       # before
       h.uploads_enabled()

       # after
       h.uploads_enabled("resource")
       h.uploads_enabled("group")
       h.uploads_enabled("user")
       h.uploads_enabled("admin")
