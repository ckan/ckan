# encoding: utf-8

import __builtin__ as builtins

import paste.fileapp
import flask
from mock import patch
from nose.tools import (assert_equal, assert_in, assert_is_instance)
from pyfakefs import fake_filesystem
from ckan.lib.helpers import url_for

import ckan.lib.uploader
import ckan.model as model
import ckan.plugins as plugins
from ckan.common import config
import ckan.tests.factories as factories
import ckan.tests.helpers as helpers
import ckanext.example_iuploader.plugin as plugin

webtest_submit = helpers.webtest_submit
submit_and_follow = helpers.submit_and_follow

real_open = open
fs = fake_filesystem.FakeFilesystem()
fake_os = fake_filesystem.FakeOsModule(fs)
fake_open = fake_filesystem.FakeFileOpen(fs)
CONTENT = b'data'


def mock_open_if_open_fails(*args, **kwargs):
    try:
        return real_open(*args, **kwargs)
    except (OSError, IOError):
        return fake_open(*args, **kwargs)


def _get_package_new_page(app):
    user = factories.User()
    env = {'REMOTE_USER': user['name'].encode('ascii')}
    response = app.get(
        url=url_for('dataset.new'),
        extra_environ=env,
    )
    return env, response


class TestExampleIUploaderPlugin(helpers.FunctionalTestBase):
    def __init__(self):
        super(TestExampleIUploaderPlugin, self).__init__()
        self.fs = None
        self.fake_open = None
        self.fake_os = None

    @classmethod
    def setup_class(cls):
        super(TestExampleIUploaderPlugin, cls).setup_class()
        plugins.load('example_iuploader')

    @classmethod
    def teardown_class(cls):
        plugins.unload('example_iuploader')
        super(TestExampleIUploaderPlugin, cls).teardown_class()

    @classmethod
    def _apply_config_changes(cls, cfg):
        cfg['ckan.storage_path'] = '/doesnt_exist'

    def setup(self):
        # Set up a fake filesystem for the uploads to be stored
        super(TestExampleIUploaderPlugin, self).setup()

    # Set up a mock open which tries the real filesystem first then falls
    # back to the mock filesystem.
    # Would be nicer if we could mock open on a specific module, but because
    # it's a builtin, it's all or nothing (and various template loaders call
    # open)
    @patch.object(ckan.lib.uploader, 'os', fake_os)
    @patch.object(builtins, 'open', side_effect=mock_open_if_open_fails)
    @patch.object(flask, 'send_file', side_effect=[CONTENT])
    @patch.object(paste.fileapp, 'os', fake_os)
    @patch.object(config['pylons.h'], 'uploads_enabled', return_value=True)
    @patch.object(ckan.lib.uploader, '_storage_path', new='/doesnt_exist')
    def test_resource_download_iuploader_called(
        self, mock_uploads_enabled, mock_open, send_file
    ):
        app = self._get_test_app()
        env, response = _get_package_new_page(app)
        form = response.forms['dataset-edit']
        dataset_name = u'package_with_resource'
        form['name'] = dataset_name
        response = submit_and_follow(app, form, env, 'save')
        form = response.forms['resource-edit']
        form['upload'] = ('README.rst', CONTENT)

        # Mock the plugin's ResourceUploader, returning the same value, but
        # tracking it's calls to make sure IUpload is being called.
        with patch.object(
            plugin.ResourceUpload,
            'get_path',
            side_effect=plugin.ResourceUpload.get_path,
            autospec=True
        ) as mock_get_path:
            response = submit_and_follow(app, form, env, 'save', 'go-metadata')
        assert_equal(mock_get_path.call_count, 1)
        assert_is_instance(
            mock_get_path.call_args[0][0], plugin.ResourceUpload
        )
        pkg = model.Package.by_name(dataset_name)
        assert_equal(mock_get_path.call_args[0][1], pkg.resources[0].id)

        assert_equal(pkg.resources[0].url_type, u'upload')
        assert_equal(pkg.state, 'active')
        url = url_for(
            'resource.download', id=pkg.id, resource_id=pkg.resources[0].id
        )

        # Mock the plugin's ResourceUploader again
        with patch.object(
            plugin.ResourceUpload,
            'get_path',
            side_effect=plugin.ResourceUpload.get_path,
            autospec=True
        ) as mock_get_path:
            response = app.get(url)
        assert_equal(mock_get_path.call_count, 1)
        assert_is_instance(
            mock_get_path.call_args[0][0], plugin.ResourceUpload
        )
        assert_equal(mock_get_path.call_args[0][1], pkg.resources[0].id)
        assert_equal(CONTENT, response.body)
