# encoding: utf-8

import os.path as path

import pytest
import six


class TestFlaskStreaming(object):

    @pytest.mark.ckan_config("ckan.plugins", "example_flask_streaming")
    def test_accordance_of_chunks(self, app):
        """Test streaming of items collection."""
        url = str("/stream/string")  # produces list of words
        resp = app.get(url)
        assert six.ensure_binary("Hello World, this is served from an extension").split() == list(
            resp.iter_encoded()
        )

    @pytest.mark.ckan_config("ckan.plugins", "example_flask_streaming")
    def test_template_streaming(self, app):
        """Test streaming of template response."""
        bound = 7
        url = str("/stream/template/{}".format(bound))  # produces nums list
        resp = app.get(url)
        content = six.ensure_binary("").join(resp.iter_encoded())
        for i in range(bound):
            assert six.ensure_binary(str(i)) in content

    @pytest.mark.ckan_config("ckan.plugins", "example_flask_streaming")
    def test_file_streaming(self, app):
        """Test streaming of existing file(10lines.txt)."""
        url = str("/stream/file")  # streams file
        resp = app.get(url)
        f_path = path.join(
            path.dirname(path.abspath(__file__)), "10lines.txt"
        )
        with open(f_path) as test_file:
            content = [six.ensure_binary(line) for line in test_file.readlines()]
            assert content == list(resp.iter_encoded())

    @pytest.mark.ckan_config("ckan.plugins", "example_flask_streaming")
    def test_render_with_context(self, app):
        """Test availability of context inside templates."""
        url = str("/stream/context?var=10")  # produces `var` value
        resp = app.get(url)
        assert six.ensure_binary("10") == resp.data
