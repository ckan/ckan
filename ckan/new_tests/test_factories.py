import nose.tools

import ckan.new_tests.helpers as helpers
import ckan.new_tests.factories as factories
import ckan.model as model

assert_equals = nose.tools.assert_equals
assert_not_equals = nose.tools.assert_not_equals


class TestFactories(object):
    @classmethod
    def setup_class(cls):
        helpers.reset_db()

    @classmethod
    def teardown_class(cls):
        helpers.reset_db()

    def test_user_factory(self):
        user1 = factories.User()
        user2 = factories.User()
        assert_not_equals(user1['id'], user2['id'])

    def test_resource_factory(self):
        resource1 = factories.Resource()
        resource2 = factories.Resource()
        assert_not_equals(resource1['id'], resource2['id'])

    def test_sysadmin_factory(self):
        sysadmin1 = factories.Sysadmin()
        sysadmin2 = factories.Sysadmin()
        assert_not_equals(sysadmin1['id'], sysadmin2['id'])

    def test_group_factory(self):
        group1 = factories.Group()
        group2 = factories.Group()
        assert_not_equals(group1['id'], group2['id'])

    def test_organization_factory(self):
        organization1 = factories.Organization()
        organization2 = factories.Organization()
        assert_not_equals(organization1['id'], organization2['id'])

    def test_related_factory(self):
        related1 = factories.Related()
        related2 = factories.Related()
        assert_not_equals(related1['id'], related2['id'])

    def test_dataset_factory(self):
        dataset1 = factories.Dataset()
        dataset2 = factories.Dataset()
        assert_not_equals(dataset1['id'], dataset2['id'])

    def test_dataset_factory_allows_creation_by_anonymous_user(self):
        dataset = factories.Dataset(user=None)
        assert_equals(dataset['creator_user_id'], None)

    def test_mockuser_factory(self):
        mockuser1 = factories.MockUser()
        mockuser2 = factories.MockUser()
        assert_not_equals(mockuser1['id'], mockuser2['id'])

    def test_member_factory_adds_user_to_group_in_specified_capacity(self):
        user_id = factories.User()['id']
        group_id = factories.Group()['id']
        capacity = 'admin'

        factories.Member(id=group_id, capacity=capacity,
                         object_type='user', object=user_id)

        user = model.User.get(user_id)
        groups = user.get_groups(group_type='group', capacity=capacity)
        user_groups_ids = [g.id for g in groups]
        error_message = "User wasn't added as %s of group %s" % \
                        (capacity, group_id)
        assert group_id in user_groups_ids, error_message

    def test_member_factory_adds_dataset_to_group_in_specified_capacity(self):
        dataset_id = factories.Dataset()['id']
        group_id = factories.Group()['id']
        capacity = 'public'

        factories.Member(id=group_id, capacity=capacity,
                         object_type='package', object=dataset_id)

        dataset = model.Package.get(dataset_id)
        groups = dataset.get_groups(group_type='group', capacity=capacity)
        dataset_groups_ids = [g.id for g in groups]
        error_message = "Dataset wasn't added as %s of group %s" % \
                        (capacity, group_id)
        assert group_id in dataset_groups_ids, error_message

    def test_member_factory_adds_parent_group_to_group(self):
        parent_group_id = factories.Group()['id']
        group_id = factories.Group()['id']
        capacity = 'parent'

        factories.Member(id=group_id, capacity=capacity,
                         object_type='group', object=parent_group_id)

        group = model.Group.get(group_id)
        parent_groups = group.get_parent_groups()
        parent_groups_ids = [g.id for g in parent_groups]
        error_message = "Group wasn't added as %s of group %s" % \
                        (capacity, group_id)
        assert parent_group_id in parent_groups_ids, error_message
