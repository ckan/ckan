# encoding: utf-8

import os.path as path

from nose.tools import eq_, assert_raises
from webtest.app import TestRequest
from webtest import lint  # NOQA
import ckan.plugins as plugins
import ckan.tests.helpers as helpers


class TestFlaskStreaming(helpers.FunctionalTestBase):

    def _get_resp(self, url):
        req = TestRequest.blank(url)
        app = lint.middleware(self.app.app)
        res = req.get_response(app, True)
        return res

    def setup(self):
        self.app = helpers._get_test_app()

        # Install plugin and register its blueprint
        if not plugins.plugin_loaded(u'example_flask_streaming'):
            plugins.load(u'example_flask_streaming')
            plugin = plugins.get_plugin(u'example_flask_streaming')
            self.app.flask_app.register_extension_blueprint(
                plugin.get_blueprint())

    def test_accordance_of_chunks(self):
        u'''Test extension sets up a unique route.'''
        url = str(u'/stream/string')
        resp = self._get_resp(url)
        eq_(
            u'Hello World, this is served from an extension'.split(),
            list(resp.app_iter))
        resp.app_iter.close()

    def test_template_streaming(self):
        u'''Test extension sets up a unique route.'''
        url = str(u'/stream/template')
        resp = self._get_resp(url)
        eq_(1, len(list(resp.app_iter)))

        url = str(u'/stream/template/7')
        resp = self._get_resp(url)
        eq_(2, len(list(resp.app_iter)))
        resp._app_iter.close()

    def test_file_streaming(self):
        u'''Test extension sets up a unique route.'''
        url = str(u'/stream/file')
        resp = self._get_resp(url)
        f_path = path.join(path.dirname(path.abspath(__file__)), u'10lines.txt')
        with open(f_path) as test_file:
            content = test_file.readlines()
            eq_(content, list(resp.app_iter))
        resp._app_iter.close()

    def test_render_with_context(self):
        u'''Test extension sets up a unique route.'''
        url = str(u'/stream/context?var=10')
        resp = self._get_resp(url)
        eq_(u'10', resp.body)

    def test_render_without_context(self):
        u'''Test extension sets up a unique route.'''
        url = str(u'/stream/without_context?var=10')
        resp = self._get_resp(url)
        assert_raises(AttributeError, u''.join, resp.app_iter)
        resp.app_iter.close()
