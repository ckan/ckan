import paste.fixture
import pylons.test
import routes

import ckan.plugins


class TestExampleITemplateHelpersPlugin:

    @classmethod
    def setup(cls):
        cls.app = paste.fixture.TestApp(pylons.test.pylonsapp)
        ckan.plugins.load('example_itemplatehelpers')

    def test(self):
        offset = routes.url_for(controller='home', action='index')
        response = self.app.get(offset)
        assert "This is some example text." in response
