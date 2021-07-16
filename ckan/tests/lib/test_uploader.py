# encoding: utf-8
import six

from werkzeug.datastructures import FileStorage

import ckan.lib.uploader
from ckan.lib.uploader import ResourceUpload, Upload


class TestInitResourceUpload(object):
    def test_resource_without_upload_with_old_werkzeug(
            self, ckan_config, monkeypatch, tmpdir):
        monkeypatch.setitem(ckan_config, 'ckan.storage_path', str(tmpdir))
        monkeypatch.setattr(ckan.lib.uploader, '_storage_path', str(tmpdir))

        # this test data is based on real observation using a browser
        # and werkzeug 0.14.1
        res = {'clear_upload': 'true',
               'format': 'CSV',
               'url': 'https://example.com/data.csv',
               'description': '',
               'upload': '',
               'package_id': 'dataset1',
               'id': '8a3a874e-5ee1-4e43-bdaf-e2569cf72344',
               'name': 'data.csv'}
        res_upload = ResourceUpload(res)

        assert res_upload.filename is None

    def test_resource_without_upload(
            self, ckan_config, monkeypatch, tmpdir):
        monkeypatch.setitem(ckan_config, 'ckan.storage_path', str(tmpdir))
        monkeypatch.setattr(ckan.lib.uploader, '_storage_path', str(tmpdir))
        # this test data is based on real observation using a browser
        res = {'clear_upload': 'true',
               'format': 'PNG',
               'url': 'https://example.com/data.csv',
               'description': '',
               'upload': FileStorage(filename=''),
               'package_id': 'dataset1',
               'id': '8a3a874e-5ee1-4e43-bdaf-e2569cf72344',
               'name': 'data.csv'}
        res_upload = ResourceUpload(res)

        assert res_upload.filename is None

    def test_resource_with_upload(
            self, ckan_config, monkeypatch, tmpdir):
        monkeypatch.setitem(ckan_config, 'ckan.storage_path', str(tmpdir))
        monkeypatch.setattr(ckan.lib.uploader, '_storage_path', str(tmpdir))
        # this test data is based on real observation using a browser
        res = {'clear_upload': '',
               'format': 'PNG',
               'url': 'https://example.com/data.csv',
               'description': '',
               'upload': FileStorage(filename='data.csv', content_type='CSV'),
               'package_id': 'dataset1',
               'id': '8a3a874e-5ee1-4e43-bdaf-e2569cf72344',
               'name': 'data.csv'}
        res_upload = ResourceUpload(res)

        assert res_upload.filesize == 0
        assert res_upload.filename == 'data.csv'


class TestUpload(object):
    def test_group_upload(self, monkeypatch, tmpdir, make_app, ckan_config):
        """Reproduce group's logo upload and check that file available through
        public url.

        """
        monkeypatch.setitem(ckan_config, 'ckan.storage_path', str(tmpdir))
        monkeypatch.setattr(ckan.lib.uploader, '_storage_path', str(tmpdir))
        group = {'clear_upload': '',
                 'upload': FileStorage(
                     six.BytesIO(six.ensure_binary('hello')),
                     filename='logo.png',
                     content_type='PNG'
                 ),
                 'name': 'test-group-upload'}
        group_upload = Upload('group')
        group_upload.update_data_dict(group, 'url', 'upload', 'clear_upload')
        group_upload.upload()
        uploads_dir = tmpdir / 'storage' / 'uploads' / 'group'
        logo = uploads_dir.listdir()[0]
        assert logo.basename == group['url']
        app = make_app()
        resp = app.get('/uploads/group/' + group['url'])
        assert resp.status_code == 200
        assert resp.body == 'hello'
