# encoding: utf-8
import six

from werkzeug.datastructures import FileStorage

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


class TestUpload(object):
    def test_group_upload(self, monkeypatch, tmpdir, make_app, ckan_config):
        """Reproduce group's logo upload and check that file available through
        public url.

        """
        monkeypatch.setitem(ckan_config, u'ckan.storage_path', str(tmpdir))
        monkeypatch.setattr(ckan.lib.uploader, u'_storage_path', str(tmpdir))
        group = {u'clear_upload': u'',
                 u'upload': FileStorage(
                     six.BytesIO(six.ensure_binary(u'hello')),
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
        assert resp.body == u'hello'
