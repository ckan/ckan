from ckan.tests import *
import ckan.model as model
from ckan.lib.create_test_data import CreateTestData
from ckan.tests.pylons_controller import PylonsTestCase
import ckan.plugins as plugins
import ckan.controllers.package as package
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
        self.calls['preview_template'] += 1


class TestPluggablePreviews(object):
    @classmethod
    def setup_class(cls):
        PylonsTestCase.setup_class()
        CreateTestData.create()

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()

    def test_hook(self):
        plugin = MockResourcePreviewExtension()
        plugins.load(plugin)

        testpackage = model.Package.get('annakarenina')

        pc = package.PackageController()
        pc.resource_datapreview(testpackage.id, testpackage.resources[0])

        assert plugin.calls['can_preview'] == 1, plugin.calls
        plugins.unload(plugin)
