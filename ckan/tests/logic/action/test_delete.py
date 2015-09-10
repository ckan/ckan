import nose.tools

import ckan.tests.helpers as helpers
import ckan.tests.factories as factories
import ckan.logic as logic
import ckan.model as model
import ckan.plugins as p

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


class TestGroupPurge(object):
    def setup(self):
        helpers.reset_db()

    def test_a_non_sysadmin_cant_purge_group(self):
        user = factories.User()
        group = factories.Group(user=user)

        assert_raises(logic.NotAuthorized,
                      helpers.call_action,
                      'group_purge',
                      context={'user': user['name'], 'ignore_auth': False},
                      id=group['name'])

    def test_purged_group_does_not_show(self):
        group = factories.Group()

        helpers.call_action('group_purge',
                            context={'ignore_auth': True},
                            id=group['name'])

        assert_raises(logic.NotFound, helpers.call_action, 'group_show',
                      context={}, id=group['name'])

    def test_purged_group_leaves_no_trace_in_the_model(self):
        factories.Group(name='parent')
        user = factories.User()
        group1 = factories.Group(name='group1',
                                 extras=[{'key': 'key1', 'value': 'val1'}],
                                 users=[{'name': user['name']}],
                                 groups=[{'name': 'parent'}])
        factories.Group(name='child', groups=[{'name': 'group1'}])
        num_revisions_before = model.Session.query(model.Revision).count()

        helpers.call_action('group_purge',
                            context={'ignore_auth': True},
                            id=group1['name'])
        num_revisions_after = model.Session.query(model.Revision).count()

        # the Group and related objects are gone
        assert_equals(sorted([g.name for g in
                              model.Session.query(model.Group).all()]),
                      ['child', 'parent'])
        assert_equals(model.Session.query(model.GroupExtra).all(), [])
        # the only members left are the users for the parent and child
        assert_equals(sorted([
            (m.table_name, m.group.name)
            for m in model.Session.query(model.Member).join(model.Group)]),
            [('user', 'child'), ('user', 'parent')])

        # the group's object revisions were purged too
        assert_equals(sorted(
            [gr.name for gr in model.Session.query(model.GroupRevision)]),
            ['child', 'parent'])
        assert_equals(model.Session.query(model.GroupExtraRevision).all(),
                      [])
        # Member is not revisioned

        # No Revision objects were purged, in fact 1 is created for the purge
        assert_equals(num_revisions_after - num_revisions_before, 1)


class TestOrganizationPurge(object):
    def setup(self):
        helpers.reset_db()

    def test_a_non_sysadmin_cant_purge_org(self):
        user = factories.User()
        org = factories.Organization(user=user)

        assert_raises(logic.NotAuthorized,
                      helpers.call_action,
                      'organization_purge',
                      context={'user': user['name'], 'ignore_auth': False},
                      id=org['name'])

    def test_purged_org_does_not_show(self):
        org = factories.Organization()

        helpers.call_action('organization_purge',
                            context={'ignore_auth': True},
                            id=org['name'])

        assert_raises(logic.NotFound, helpers.call_action, 'organization_show',
                      context={}, id=org['name'])

    def test_purged_organization_leaves_no_trace_in_the_model(self):
        factories.Organization(name='parent')
        user = factories.User()
        org1 = factories.Organization(
            name='org1',
            extras=[{'key': 'key1', 'value': 'val1'}],
            users=[{'name': user['name']}],
            groups=[{'name': 'parent'}])
        factories.Organization(name='child', groups=[{'name': 'group1'}])
        num_revisions_before = model.Session.query(model.Revision).count()

        helpers.call_action('organization_purge',
                            context={'ignore_auth': True},
                            id=org1['name'])
        num_revisions_after = model.Session.query(model.Revision).count()

        # the Organization and related objects are gone
        assert_equals(sorted([o.name for o in
                              model.Session.query(model.Group).all()]),
                      ['child', 'parent'])
        assert_equals(model.Session.query(model.GroupExtra).all(), [])
        # the only members left are the users for the parent and child
        assert_equals(sorted([
            (m.table_name, m.group.name)
            for m in model.Session.query(model.Member).join(model.Group)]),
            [('user', 'child'), ('user', 'parent')])

        # the organization's object revisions were purged too
        assert_equals(sorted(
            [gr.name for gr in model.Session.query(model.GroupRevision)]),
            ['child', 'parent'])
        assert_equals(model.Session.query(model.GroupExtraRevision).all(),
                      [])
        # Member is not revisioned

        # No Revision objects were purged, in fact 1 is created for the purge
        assert_equals(num_revisions_after - num_revisions_before, 1)
