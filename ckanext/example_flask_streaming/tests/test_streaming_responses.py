# encoding: utf-8

import os.path as path

import pytest
import six
from webtest.app import TestRequest
from webtest import lint  # NOQA


class TestFlaskStreaming(object):
    @pytest.fixture
    def get_response(self, app):
        def _get_resp(url):
            req = TestRequest.blank(url)
            res = req.get_response(lint.middleware(app.app), True)
            return res

        return _get_resp

    @pytest.mark.ckan_config(u"ckan.plugins", u"example_flask_streaming")
    def test_accordance_of_chunks(self, get_response):
        u"""Test streaming of items collection."""
        url = str(u"/stream/string")  # produces list of words
        resp = get_response(url)
        assert six.ensure_binary(u"Hello World, this is served from an extension").split() == list(
            resp.app_iter
        )
        resp.app_iter.close()

    @pytest.mark.ckan_config(u"ckan.plugins", u"example_flask_streaming")
    def test_template_streaming(self, get_response):
        u"""Test streaming of template response."""
        bound = 7
        url = str(u"/stream/template/{}".format(bound))  # produces nums list
        resp = get_response(url)
        content = six.ensure_binary(u"").join(resp.app_iter)
        for i in range(bound):
            assert six.ensure_binary(str(i)) in content
        resp._app_iter.close()

    @pytest.mark.ckan_config(u"ckan.plugins", u"example_flask_streaming")
    def test_file_streaming(self, get_response):
        u"""Test streaming of existing file(10lines.txt)."""
        url = str(u"/stream/file")  # streams file
        resp = get_response(url)
        f_path = path.join(
            path.dirname(path.abspath(__file__)), u"10lines.txt"
        )
        with open(f_path) as test_file:
            content = [six.ensure_binary(line) for line in test_file.readlines()]
            assert content == list(resp.app_iter)
        resp._app_iter.close()

    @pytest.mark.ckan_config(u"ckan.plugins", u"example_flask_streaming")
    def test_render_with_context(self, get_response):
        u"""Test availability of context inside templates."""
        url = str(u"/stream/context?var=10")  # produces `var` value
        resp = get_response(url)
        assert six.ensure_binary(u"10") == resp.body

    @pytest.mark.ckan_config(u"ckan.plugins", u"example_flask_streaming")
    def test_render_without_context(self, get_response):
        u"""
        Test that error raised if there is an
        attempt to pick variable if context is not provider.
        """
        url = str(u"/stream/without_context?var=10")
        resp = get_response(url)
        with pytest.raises(AttributeError):
            u"".join(resp.app_iter)
        resp.app_iter.close()
