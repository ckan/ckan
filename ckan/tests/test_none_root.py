# encoding: utf-8
from pylons import config
import ckan.plugins as p
import ckan.tests.helpers as helpers


class TestNoneRootCKAN():
    @helpers.change_config(u'ckan.root_path', u'/data/{{LANG}}')
    def test_resource_url(self):
        app = helpers._get_test_app()

        p.load(u'example_theme_v15_fanstatic')
        content = app.get(u'/en/base.html')
        assert u'example_theme.min.css' in content
        assert u'href="/data/fanstatic/example_theme' in content
        p.unload(u'example_theme_v15_fanstatic')
