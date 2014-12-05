from ckan.new_tests import factories, helpers
from ckan import model


class TestRevisioning:
    @classmethod
    def setup_class(cls):
        helpers.reset_db()

    def setup(self):
        model.repo.rebuild_db()

    def test_revision_update_without_change(self):
        # https://github.com/ckan/ckan/issues/1779
        dataset = factories.Dataset()
        resource = factories.Resource(package_id=dataset['id'],
                                      url='http://url1')
        resource['url'] = 'http://url2'
        helpers.call_action('resource_update', **resource)
        assert helpers.call_action('package_show', id=dataset['id'])['resources']
        helpers.call_action('resource_update', **resource)
        # The next assert fails if the resource going missing
        assert helpers.call_action('package_show', id=dataset['id'])['resources']
