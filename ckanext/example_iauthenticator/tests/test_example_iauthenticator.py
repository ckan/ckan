# encoding: utf-8

from ckan.tests import helpers
import ckan.plugins as p

toolkit = p.toolkit


class TestExampleIAuthenticator(helpers.FunctionalTestBase):

    def setup(self):
        self.app = helpers._get_test_app()

        # Install plugin and register its blueprint
        if not p.plugin_loaded(u'example_iauthenticator'):
            p.load(u'example_iauthenticator')
            plugin = p.get_plugin(u'example_iauthenticator')
            self.app.flask_app.register_extension_blueprint(plugin.get_blueprint()[0])

    def test_identify_sets_cookie(self):

        resp = self.app.get(toolkit.url_for(u'home.index'))

        assert u'example_iauthenticator=hi' in resp.headers[u'Set-Cookie']

    def test_login_redirects(self):

        resp = self.app.get(
            toolkit.url_for(u'user.login'),
        )

        assert resp.status_int == 302
        assert resp.headers[u'Location'] == toolkit.url_for(u'example_iauthenticator.custom_login', _external=True)

    def test_logout_redirects(self):

        resp = self.app.get(
            toolkit.url_for(u'user.logout'),
        )

        assert resp.status_int == 302
        assert resp.headers[u'Location'] == toolkit.url_for(u'example_iauthenticator.custom_logout', _external=True)
