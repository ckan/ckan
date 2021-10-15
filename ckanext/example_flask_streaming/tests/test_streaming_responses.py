# encoding: utf-8

import os.path as path

import pytest
import six


class TestFlaskStreaming(object):

    @pytest.mark.ckan_config(u"ckan.plugins", u"example_flask_streaming")
    def test_accordance_of_chunks(self, app):
        u"""Test streaming of items collection."""
        url = str(u"/stream/string")  # produces list of words
        resp = app.get(url)
        assert (u"Hello World, this is served from an extension").encode().split() == list(
            resp.iter_encoded()
        )

    @pytest.mark.ckan_config(u"ckan.plugins", u"example_flask_streaming")
    def test_template_streaming(self, app):
        u"""Test streaming of template response."""
        bound = 7
        url = str(u"/stream/template/{}".format(bound))  # produces nums list
        resp = app.get(url)
        content = (u"").encode().join(resp.iter_encoded())
        for i in range(bound):
            assert (str(i)).encode() in content

    @pytest.mark.ckan_config(u"ckan.plugins", u"example_flask_streaming")
    def test_file_streaming(self, app):
        u"""Test streaming of existing file(10lines.txt)."""
        url = str(u"/stream/file")  # streams file
        resp = app.get(url)
        f_path = path.join(
            path.dirname(path.abspath(__file__)), u"10lines.txt"
        )
        with open(f_path) as test_file:
            content = [(line).encode() for line in test_file.readlines()]
            assert content == list(resp.iter_encoded())

    @pytest.mark.ckan_config(u"ckan.plugins", u"example_flask_streaming")
    def test_render_with_context(self, app):
        u"""Test availability of context inside templates."""
        url = str(u"/stream/context?var=10")  # produces `var` value
        resp = app.get(url)
        assert (u"10").encode() == resp.data
