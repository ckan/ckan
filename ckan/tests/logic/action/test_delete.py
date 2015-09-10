import nose.tools

import ckan.tests.helpers as helpers
import ckan.tests.factories as factories
import ckan.logic as logic
import ckan.model as model
import ckan.plugins as p
import ckan.lib.search as search

assert_equals = nose.tools.assert_equals
assert_raises = nose.tools.assert_raises


class TestDelete:

    def setup(self):
        helpers.reset_db()

    def test_resource_delete(self):
        user = factories.User()
        sysadmin = factories.Sysadmin()
        resource = factories.Resource(user=user)
        context = {}
        params = {'id': resource['id']}

        helpers.call_action('resource_delete', context, **params)

        # Not even a sysadmin can see it now
        assert_raises(logic.NotFound, helpers.call_action, 'resource_show',
                      {'user': sysadmin['name']}, **params)
        # It is still there but with state=deleted
        res_obj = model.Resource.get(resource['id'])
        assert_equals(res_obj.state, 'deleted')


class TestDeleteResourceViews(object):

    @classmethod
    def setup_class(cls):
        if not p.plugin_loaded('image_view'):
            p.load('image_view')

        helpers.reset_db()

    @classmethod
    def teardown_class(cls):
        p.unload('image_view')

    def test_resource_view_delete(self):
        resource_view = factories.ResourceView()

        params = {'id': resource_view['id']}

        helpers.call_action('resource_view_delete', context={}, **params)

        assert_raises(logic.NotFound, helpers.call_action, 'resource_view_show',
                      context={}, **params)

        # The model object is actually deleted
        resource_view_obj = model.ResourceView.get(resource_view['id'])
        assert_equals(resource_view_obj, None)

    def test_delete_no_id_raises_validation_error(self):

        params = {}

        assert_raises(logic.ValidationError, helpers.call_action, 'resource_view_delete',
                      context={}, **params)

    def test_delete_wrong_id_raises_not_found_error(self):

        params = {'id': 'does_not_exist'}

        assert_raises(logic.NotFound, helpers.call_action, 'resource_view_delete',
                      context={}, **params)


class TestClearResourceViews(object):

    @classmethod
    def setup_class(cls):
        if not p.plugin_loaded('image_view'):
            p.load('image_view')
        if not p.plugin_loaded('recline_view'):
            p.load('recline_view')

        helpers.reset_db()

    @classmethod
    def teardown_class(cls):
        p.unload('image_view')
        p.unload('recline_view')

    def test_resource_view_clear(self):
        factories.ResourceView(view_type='image_view')
        factories.ResourceView(view_type='image_view')

        factories.ResourceView(view_type='recline_view')
        factories.ResourceView(view_type='recline_view')

        count = model.Session.query(model.ResourceView).count()

        assert_equals(count, 4)

        helpers.call_action('resource_view_clear', context={})

        count = model.Session.query(model.ResourceView).count()

        assert_equals(count, 0)

    def test_resource_view_clear_with_types(self):
        factories.ResourceView(view_type='image_view')
        factories.ResourceView(view_type='image_view')

        factories.ResourceView(view_type='recline_view')
        factories.ResourceView(view_type='recline_view')

        count = model.Session.query(model.ResourceView).count()

        assert_equals(count, 4)

        helpers.call_action('resource_view_clear', context={},
                            view_types=['image_view'])

        view_types = model.Session.query(model.ResourceView.view_type).all()

        assert_equals(len(view_types), 2)
        for view_type in view_types:
            assert_equals(view_type[0], 'recline_view')


class TestDeleteTags(object):

    def test_tag_delete_with_unicode_returns_unicode_error(self):
        # There is not a lot of call for it, but in theory there could be
        # unicode in the ActionError error message, so ensure that comes
        # through in NotFound as unicode.
        try:
            helpers.call_action('tag_delete', id=u'Delta symbol: \u0394')
        except logic.NotFound, e:
            assert u'Delta symbol: \u0394' in unicode(e)
        else:
            assert 0, 'Should have raised NotFound'


class TestDatasetPurge(object):
    def setup(self):
        helpers.reset_db()

    def test_a_non_sysadmin_cant_purge_dataset(self):
        user = factories.User()
        dataset = factories.Dataset(user=user)

        assert_raises(logic.NotAuthorized,
                      helpers.call_action,
                      'dataset_purge',
                      context={'user': user['name'], 'ignore_auth': False},
                      id=dataset['name'])

    def test_purged_dataset_does_not_show(self):
        dataset = factories.Dataset()

        helpers.call_action('dataset_purge',
                            context={'ignore_auth': True},
                            id=dataset['name'])

        assert_raises(logic.NotFound, helpers.call_action, 'package_show',
                      context={}, id=dataset['name'])

    def test_purged_dataset_is_not_listed(self):
        dataset = factories.Dataset()

        helpers.call_action('dataset_purge', id=dataset['name'])

        assert_equals(helpers.call_action('package_list', context={}), [])

    def test_group_no_longer_shows_its_purged_dataset(self):
        group = factories.Group()
        dataset = factories.Dataset(groups=[{'name': group['name']}])

        helpers.call_action('dataset_purge', id=dataset['name'])

        dataset_shown = helpers.call_action('group_show', context={},
                                            id=group['id'],
                                            include_datasets=True)
        assert_equals(dataset_shown['packages'], [])

    def test_purged_dataset_is_not_in_search_results(self):
        search.clear()
        dataset = factories.Dataset()
        def get_search_results():
            results = helpers.call_action('package_search',
                                          q=dataset['title'])['results']
            return [d['name'] for d in results]
        assert_equals(get_search_results(), [dataset['name']])

        helpers.call_action('dataset_purge', id=dataset['name'])

        assert_equals(get_search_results(), [])

    def test_purged_dataset_leaves_no_trace_in_the_model(self):
        factories.Group(name='group1')
        org = factories.Organization()
        dataset = factories.Dataset(
            tags=[{'name': 'tag1'}],
            groups=[{'name': 'group1'}],
            owner_org=org['id'],
            extras=[{'key': 'testkey', 'value': 'testvalue'}])
        num_revisions_before = model.Session.query(model.Revision).count()

        helpers.call_action('dataset_purge',
                            context={'ignore_auth': True},
                            id=dataset['name'])
        num_revisions_after = model.Session.query(model.Revision).count()

        # the Package and related objects are gone
        assert_equals(model.Session.query(model.Package).all(), [])
        assert_equals(model.Session.query(model.PackageTag).all(), [])
        # there is no clean-up of the tag object itself, just the PackageTag.
        assert_equals([t.name for t in model.Session.query(model.Tag).all()],
                      ['tag1'])
        assert_equals(model.Session.query(model.PackageExtra).all(), [])
        # the only member left is for the user created in factories.Group() and
        # factories.Organization()
        assert_equals([(m.table_name, m.group.name)
                       for m in model.Session.query(model.Member).join(model.Group)],
                      [('user', 'group1'), ('user', 'test_org_0')])

        # all the object revisions were purged too
        assert_equals(model.Session.query(model.PackageRevision).all(), [])
        assert_equals(model.Session.query(model.PackageTagRevision).all(), [])
        assert_equals(model.Session.query(model.PackageExtraRevision).all(),
                      [])
        # Member is not revisioned

        # No Revision objects were purged, in fact 1 is created for the purge
        assert_equals(num_revisions_after - num_revisions_before, 1)

    def test_missing_id_returns_error(self):
        assert_raises(logic.ValidationError,
                      helpers.call_action, 'dataset_purge')

    def test_bad_id_returns_404(self):
        assert_raises(logic.NotFound,
                      helpers.call_action, 'dataset_purge', id='123')
