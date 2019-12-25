# encoding: utf-8

import flask
import pytest
import six
from mock import patch
from pyfakefs import fake_filesystem
from ckan.lib.helpers import url_for

import ckan.lib.uploader
import ckan.model as model
import ckan.plugins as plugins
from ckan.common import config
import ckan.tests.factories as factories
import ckan.tests.helpers as helpers
import ckanext.example_iuploader.plugin as plugin

try:
    import __builtin__ as builtins
except ImportError:
    import builtins

webtest_submit = helpers.webtest_submit
submit_and_follow = helpers.submit_and_follow

real_open = open
fs = fake_filesystem.FakeFilesystem()
fake_os = fake_filesystem.FakeOsModule(fs)
fake_open = fake_filesystem.FakeFileOpen(fs)
CONTENT = b"data"


def mock_open_if_open_fails(*args, **kwargs):
    try:
        return real_open(*args, **kwargs)
    except (OSError, IOError):
        return fake_open(*args, **kwargs)


def _get_package_new_page(app):
    user = factories.User()
    env = {"REMOTE_USER": six.ensure_str(user["name"])}
    response = app.get(url=url_for("dataset.new"), extra_environ=env)
    return env, response


# Uses a fake filesystem for the uploads to be stored.
# Set up a mock open which tries the real filesystem first then falls
# back to the mock filesystem.
# Would be nicer if we could mock open on a specific module, but because
# it's a builtin, it's all or nothing (and various template loaders call
# open)
@pytest.mark.ckan_config("ckan.plugins", "example_iuploader")
@pytest.mark.ckan_config("ckan.webassets.path", "/tmp/webassets")
@pytest.mark.usefixtures("with_plugins", "clean_db")
@patch.object(ckan.lib.uploader, "os", fake_os)
@patch.object(flask, "send_file", side_effect=[CONTENT])
@patch.object(config["pylons.h"], "uploads_enabled", return_value=True)
@patch.object(ckan.lib.uploader, "_storage_path", new="/doesnt_exist")
def test_resource_download_iuploader_called(
        mock_uploads_enabled, send_file, app, monkeypatch
):
    monkeypatch.setattr(builtins, 'open', mock_open_if_open_fails)
    env, response = _get_package_new_page(app)
    form = response.forms["dataset-edit"]
    dataset_name = u"package_with_resource"
    form["name"] = dataset_name
    response = submit_and_follow(app, form, env, "save")
    form = response.forms["resource-edit"]
    form["upload"] = ("README.rst", CONTENT)

    # Mock the plugin's ResourceUploader, returning the same value, but
    # tracking it's calls to make sure IUpload is being called.
    with patch.object(
        plugin.ResourceUpload,
        "get_path",
        side_effect=plugin.ResourceUpload.get_path,
        autospec=True,
    ) as mock_get_path:
        response = submit_and_follow(app, form, env, "save", "go-metadata")
    assert mock_get_path.call_count == 1
    assert isinstance(mock_get_path.call_args[0][0], plugin.ResourceUpload)
    pkg = model.Package.by_name(dataset_name)
    assert mock_get_path.call_args[0][1] == pkg.resources[0].id

    assert pkg.resources[0].url_type == u"upload"
    assert pkg.state == "active"
    url = url_for(
        "resource.download", id=pkg.id, resource_id=pkg.resources[0].id
    )

    # Mock the plugin's ResourceUploader again
    with patch.object(
        plugin.ResourceUpload,
        "get_path",
        side_effect=plugin.ResourceUpload.get_path,
        autospec=True,
    ) as mock_get_path:
        response = app.get(url)
    assert mock_get_path.call_count == 1
    assert isinstance(mock_get_path.call_args[0][0], plugin.ResourceUpload)
    assert mock_get_path.call_args[0][1] == pkg.resources[0].id
    assert CONTENT == response.body
