from ckan.tests import *
import ckan.lib.helpers as h
import ckan.model as model
from ckan.lib.create_test_data import CreateTestData
from ckan.tests.functional.base import FunctionalTestCase
import ckan.plugins as plugins
import ckan.tests.mock_plugin as mock


class MockResourcePreviewExtension(mock.MockSingletonPlugin):
    plugins.implements(plugins.IResourcePreview)

    def __init__(self):
        from collections import defaultdict
        self.calls = defaultdict(int)

    def can_preview(self, data_dict):
        self.calls['can_preview'] += 1
        return True

    def setup_template_variables(self, context, data_dict):
        self.calls['setup_template_variables'] += 1

    def preview_template(self, context, data_dict):
        self.calls['preview_templates'] += 1
        return 'tests/mock_resource_preview_template.html'


class TestPluggablePreviews(FunctionalTestCase):
    @classmethod
    def setup_class(cls):
        cls.plugin = MockResourcePreviewExtension()
        plugins.load(cls.plugin)
        CreateTestData.create()

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()
        plugins.unload(cls.plugin)

    def test_hook(self):
        '''
        TODO:
            * Modify mock plugin to only preview resources of type 'mock'
            * Create a dataset with two resources (logic function), one of type mock and one
            of another type, and check that the mock stuff is only rendered on
            the relevant one and not the other
            * (?) create resources of type csv, json and pdf and look if the relevant bits
            are rendered (these tests should probably go in their relevant extensions)

        '''



        testpackage = model.Package.get('annakarenina')

        offset = h.url_for(controller='package',
                action='resource_datapreview',
                id=testpackage.id,
                resource_id=testpackage.resources[0].id)
        result = self.app.get(offset, status=200)

        assert 'mock-preview' in result.body
        assert 'mock-preview.js' in result.body

        assert self.plugin.calls['can_preview'] == 1, plugin.call
        assert self.plugin.calls['setup_template_variables'] == 1, plugin.calls
        assert self.plugin.calls['preview_templates'] == 1, plugin.calls
