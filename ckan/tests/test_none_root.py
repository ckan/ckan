# encoding: utf-8

from ckan.common import config
import ckan.plugins as p
import ckan.config.middleware as middleware
import webtest
import ckan.tests.helpers as helpers


class TestNoneRootCKAN():
    @helpers.change_config(u'ckan.root_path', u'/data/{{LANG}}')
    def test_resource_url(self):
        wsgiapp = middleware.make_app(config[u'global_conf'], **config)
        app = webtest.TestApp(wsgiapp)
        p.load(u'example_theme_v15_fanstatic')
        content = app.get(u'/en/base.html')
        if u'example_theme.css' not in content:
            assert u'example_theme.min.css' in content
        assert u'href="/data/fanstatic/example_theme' in content
        p.unload(u'example_theme_v15_fanstatic')
