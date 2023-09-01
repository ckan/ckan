# encoding: utf-8
import pytest
import six

from werkzeug.datastructures import FileStorage

from ckan.logic import ValidationError
import ckan.lib.uploader
from ckan.lib.uploader import ResourceUpload, Upload


class TestInitResourceUpload(object):
    def test_resource_without_upload_with_old_werkzeug(
            self, ckan_config, monkeypatch, tmpdir):
        monkeypatch.setitem(ckan_config, u'ckan.storage_path', str(tmpdir))
        monkeypatch.setattr(ckan.lib.uploader, u'_storage_path', str(tmpdir))

        # this test data is based on real observation using a browser
        # and werkzeug 0.14.1
        res = {u'clear_upload': u'true',
               u'format': u'CSV',
               u'url': u'https://example.com/data.csv',
               u'description': u'',
               u'upload': u'',
               u'package_id': u'dataset1',
               u'id': u'8a3a874e-5ee1-4e43-bdaf-e2569cf72344',
               u'name': u'data.csv'}
        res_upload = ResourceUpload(res)

        assert res_upload.filename is None

    def test_resource_without_upload(
            self, ckan_config, monkeypatch, tmpdir):
        monkeypatch.setitem(ckan_config, u'ckan.storage_path', str(tmpdir))
        monkeypatch.setattr(ckan.lib.uploader, u'_storage_path', str(tmpdir))
        # this test data is based on real observation using a browser
        res = {u'clear_upload': u'true',
               u'format': u'PNG',
               u'url': u'https://example.com/data.csv',
               u'description': u'',
               u'upload': FileStorage(filename=u''),
               u'package_id': u'dataset1',
               u'id': u'8a3a874e-5ee1-4e43-bdaf-e2569cf72344',
               u'name': u'data.csv'}
        res_upload = ResourceUpload(res)

        assert res_upload.filename is None

    def test_resource_with_upload(
            self, ckan_config, monkeypatch, tmpdir):
        monkeypatch.setitem(ckan_config, u'ckan.storage_path', str(tmpdir))
        monkeypatch.setattr(ckan.lib.uploader, u'_storage_path', str(tmpdir))
        # this test data is based on real observation using a browser
        res = {u'clear_upload': u'',
               u'format': u'PNG',
               u'url': u'https://example.com/data.csv',
               u'description': u'',
               u'upload': FileStorage(filename=u'data.csv', content_type=u'CSV'),
               u'package_id': u'dataset1',
               u'id': u'8a3a874e-5ee1-4e43-bdaf-e2569cf72344',
               u'name': u'data.csv'}
        res_upload = ResourceUpload(res)

        assert res_upload.filesize == 0
        assert res_upload.filename == u'data.csv'

    def test_resource_with_dodgy_id(
            self, ckan_config, monkeypatch, tmpdir):
        monkeypatch.setitem(ckan_config, u'ckan.storage_path', str(tmpdir))
        monkeypatch.setattr(ckan.lib.uploader, u'_storage_path', str(tmpdir))

        resource_id = u'aaabbb/../../../../nope.txt'
        res = {u'clear_upload': u'',
               u'format': u'PNG',
               u'url': u'https://example.com/data.csv',
               u'description': u'',
               u'upload': FileStorage(filename=u'data.csv', content_type=u'CSV'),
               u'package_id': u'dataset1',
               u'id': resource_id,
               u'name': u'data.csv'}
        res_upload = ResourceUpload(res)

        with pytest.raises(ValidationError):
            res_upload.upload(resource_id)


class TestUpload(object):
    def test_group_upload(self, monkeypatch, tmpdir, make_app, ckan_config):
        """Reproduce group's logo upload and check that file available through
        public url.

        """
        monkeypatch.setitem(ckan_config, u'ckan.storage_path', str(tmpdir))
        monkeypatch.setattr(ckan.lib.uploader, u'_storage_path', str(tmpdir))
        some_png = """
        89 50 4E 47 0D 0A 1A 0A 00 00 00 0D 49 48 44 52
        00 00 00 01 00 00 00 01 08 02 00 00 00 90 77 53
        DE 00 00 00 0C 49 44 41 54 08 D7 63 F8 CF C0 00
        00 03 01 01 00 18 DD 8D B0 00 00 00 00 49 45 4E
        44 AE 42 60 82"""
        some_png = some_png.replace(u' ', u'').replace(u'\n', u'')
        some_png_bytes = bytes(bytearray.fromhex(some_png))

        group = {u'clear_upload': u'',
                 u'upload': FileStorage(
                     six.BytesIO(some_png_bytes),
                     filename=u'logo.png',
                     content_type=u'PNG'
                 ),
                 u'name': u'test-group-upload'}
        group_upload = Upload(u'group')
        group_upload.update_data_dict(group, u'url', u'upload', u'clear_upload')
        group_upload.upload()
        uploads_dir = tmpdir / u'storage' / u'uploads' / u'group'
        logo = uploads_dir.listdir()[0]
        assert logo.basename == group[u'url']
        app = make_app()
        resp = app.get(u'/uploads/group/' + group[u'url'])
        assert resp.status_code == 200
        # PNG signature
        if six.PY3:
            assert resp.data.hex()[:16].upper() == u'89504E470D0A1A0A'
        else:
            assert resp.data.encode(u"hex")[:16].upper() == u'89504E470D0A1A0A'
