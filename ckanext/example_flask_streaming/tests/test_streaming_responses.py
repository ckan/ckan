# encoding: utf-8

import os.path as path

from nose.tools import eq_, assert_raises, ok_
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
                plugin.get_blueprint()
            )

    def test_accordance_of_chunks(self):
        u'''Test streaming of items collection.'''
        url = str(u'/stream/string')  # produces list of words
        resp = self._get_resp(url)
        eq_(
            u'Hello World, this is served from an extension'.split(),
            list(resp.app_iter)
        )
        resp.app_iter.close()

    def test_template_streaming(self):
        u'''Test streaming of template response.'''
        bound = 7
        url = str(u'/stream/template/{}'.format(bound))  # produces nums list
        resp = self._get_resp(url)
        content = u''.join(resp.app_iter)
        for i in range(bound):
            ok_(str(i) in content)
        resp._app_iter.close()

    def test_file_streaming(self):
        u'''Test streaming of existing file(10lines.txt).'''
        url = str(u'/stream/file')  # streams file
        resp = self._get_resp(url)
        f_path = path.join(
            path.dirname(path.abspath(__file__)), u'10lines.txt'
        )
        with open(f_path) as test_file:
            content = test_file.readlines()
            eq_(content, list(resp.app_iter))
        resp._app_iter.close()

    def test_render_with_context(self):
        u'''Test availability of context inside templates.'''
        url = str(u'/stream/context?var=10')  # produces `var` value
        resp = self._get_resp(url)
        eq_(u'10', resp.body)

    def test_render_without_context(self):
        u'''
        Test that error raised if there is an
        attempt to pick variable if context is not provider.
        '''
        url = str(u'/stream/without_context?var=10')
        resp = self._get_resp(url)
        assert_raises(AttributeError, u''.join, resp.app_iter)
        resp.app_iter.close()
