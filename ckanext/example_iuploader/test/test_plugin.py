# encoding: utf-8

import flask
import pytest
import six
from mock import patch
from ckan.lib.helpers import url_for

from six.moves.urllib.parse import urlparse
import ckan.lib.uploader
import ckan.model as model

import ckan.tests.factories as factories
import ckanext.example_iuploader.plugin as plugin


CONTENT = "data"


# Uses a fake filesystem for the uploads to be stored.
# Set up a mock open which tries the real filesystem first then falls
# back to the mock filesystem.
# Would be nicer if we could mock open on a specific module, but because
# it's a builtin, it's all or nothing (and various template loaders call
# open)
@pytest.mark.ckan_config("ckan.plugins", "example_iuploader")
@pytest.mark.ckan_config("ckan.webassets.path", "/tmp/webassets")
@pytest.mark.usefixtures("with_plugins", "clean_db", "with_request_context")
@patch.object(flask, "send_file", side_effect=[CONTENT])
def test_resource_download_iuploader_called(
        send_file, app, monkeypatch, tmpdir, ckan_config
):
    monkeypatch.setitem(ckan_config, u'ckan.storage_path', str(tmpdir))
    monkeypatch.setattr(ckan.lib.uploader, u'_storage_path', str(tmpdir))

    user = factories.User()
    env = {"REMOTE_USER": six.ensure_str(user["name"])}
    url = url_for("dataset.new")

    dataset_name = u"package_with_resource"
    form = {
        "name": dataset_name,
        "save": "",
        "_ckan_phase": 1
    }
    response = app.post(
        url, data=form, environ_overrides=env, follow_redirects=False)
    location = response.headers['location']
    location = urlparse(location)._replace(scheme='', netloc='').geturl()

    # Mock the plugin's ResourceUploader, returning the same value, but
    # tracking it's calls to make sure IUpload is being called.
    with patch.object(
        plugin.ResourceUpload,
        "get_path",
        side_effect=plugin.ResourceUpload.get_path,
        autospec=True,
    ) as mock_get_path:
        response = app.post(location, environ_overrides=env, data={
            "id": "",
            "url": "http://example.com/resource",
            "save": "go-metadata",
            "upload": ("README.rst", CONTENT)
        })
    assert mock_get_path.call_count == 3
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
