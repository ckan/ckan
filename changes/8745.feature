Added support of file storages: :ref:`using-configured-storages`.

:py:class:`~ckan.lib.uploader.Upload` and
:py:class:`~ckan.lib.uploader.ResourceUpload` use filesystem storage by
default. Some of its attributes were replaced by an optional ``storage``
attribute:

* ``storage_path``: available as ``upload.storage.settings.path``
* ``filepath``: can be build by joining ``path`` from storage's settings and ``upload.filename``
* ``old_filepath``: can be build by joining ``path`` from storage's settings and ``upload.old_filename``

``upload_file`` attribute contains :py:class:`ckan.lib.files.Upload` instead of
werkzeug's ``FileStorage``.

Information about storages is validated and cached at application
startup. Tests that modify ``ckan.storage_path`` must call new
``reset_storages`` fixture after the modification to apply changes.

    # before
    def test_smth(ckan_config, monkeypatch, tmpdir):
        monkeypatch.setitem(ckan_config, "ckan.storage_path", str(tmpdir))
        ...

    # after
    def test_smth(
        ckan_config, monkeypatch, tmpdir,
        reset_storages,  # new fixture
    ):
        monkeypatch.setitem(ckan_config, "ckan.storage_path", str(tmpdir))
        reset_storages()  # reset storages to apply changes
        ...
