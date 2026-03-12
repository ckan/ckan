Added support of file storages: :ref:`using-configured-storages`.

When either ``default`` storage, or individual storages for resource, group,
user and admin uploads are configured, :py:class:`~ckan.lib.uploader.Upload`
and :py:class:`~ckan.lib.uploader.ResourceUpload` are replaced by
:py:class:`~ckan.lib.uploader.FkUpload` and
:py:class:`~ckan.lib.uploader.FkResourceUpload`. These new classes use
configurable storages and serve the role of the bridge between classic file
management system in CKAN and the new one.

New classes resemble original versions with certain attributes unified under a
new ``storage`` attribute:

* ``storage_path``: available as ``upload.storage.settings.path``
* ``filepath``: can be built by joining ``path`` from storage's settings and ``upload.filename``
* ``old_filepath``: can be built by joining ``path`` from storage's settings and ``upload.old_filename``

``upload_file`` attribute contains :py:class:`ckan.lib.files.Upload` instead of
werkzeug's ``FileStorage``.
