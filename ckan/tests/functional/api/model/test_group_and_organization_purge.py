'''Functional tests for the group_ and organization_purge APIs.

'''
import ckan.model as model
import ckan.tests as tests

import paste
import pylons.test


class TestGroupAndOrganizationPurging(object):
    '''Tests for the group_ and organization_purge APIs.

    '''
    @classmethod
    def setup_class(cls):
        cls.app = paste.fixture.TestApp(pylons.test.pylonsapp)

        # Make a sysadmin user.
        cls.sysadmin = model.User(name='test_sysadmin', sysadmin=True)
        model.Session.add(cls.sysadmin)
        model.Session.commit()
        model.Session.remove()

        # A package that will be added to our test groups and organizations.
        cls.package = tests.call_action_api(cls.app, 'package_create',
                                            name='test_package',
                                            apikey=cls.sysadmin.apikey)

        # A user who will not be a member of our test groups or organizations.
        cls.visitor = tests.call_action_api(cls.app, 'user_create',
                                            name='non_member',
                                            email='blah',
                                            password='farm',
                                            apikey=cls.sysadmin.apikey)

        # A user who will become a member of our test groups and organizations.
        cls.member = tests.call_action_api(cls.app, 'user_create',
                                           name='member',
                                           email='blah',
                                           password='farm',
                                           apikey=cls.sysadmin.apikey)

        # A user who will become an editor of our test groups and
        # organizations.
        cls.editor = tests.call_action_api(cls.app, 'user_create',
                                           name='editor',
                                           email='blah',
                                           password='farm',
                                           apikey=cls.sysadmin.apikey)

        # A user who will become an admin of our test groups and organizations.
        cls.admin = tests.call_action_api(cls.app, 'user_create',
                                          name='admin',
                                          email='blah',
                                          password='farm',
                                          apikey=cls.sysadmin.apikey)

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()

    def _organization_create(self, organization_name):
        '''Return an organization with some users and a dataset.'''

        # Make an organization with some users.
        users = [{'name': self.member['name'], 'capacity': 'member'},
                 {'name': self.editor['name'], 'capacity': 'editor'},
                 {'name': self.admin['name'], 'capacity': 'admin'}]
        organization = tests.call_action_api(self.app, 'organization_create',
                                             apikey=self.sysadmin.apikey,
                                             name=organization_name,
                                             users=users)

        # Add a dataset to the organization (have to do this separately
        # because the packages param of organization_create doesn't work).
        tests.call_action_api(self.app, 'package_update',
                              name=self.package['name'],
                              owner_org=organization['name'],
                              apikey=self.sysadmin.apikey)

        return organization

    def _group_create(self, group_name):
        '''Return a group with some users and a dataset.'''

        # Make a group with some users and a dataset.
        group = tests.call_action_api(self.app, 'group_create',
                                      apikey=self.sysadmin.apikey,
                                      name=group_name,
                                      users=[
                                          {'name': self.member['name'],
                                           'capacity': 'member',
                                           },
                                          {'name': self.editor['name'],
                                           'capacity': 'editor',
                                           },
                                          {'name': self.admin['name'],
                                           'capacity': 'admin',
                                           }],
                                      packages=[
                                          {'id': self.package['name']}],
                                      )

        return group

    def _test_group_or_organization_purge(self, name, by_id, is_org):
        '''Create a group or organization with the given name, and test
        purging it.

        :param name: the name of the group or organization to create and purge
        :param by_id: if True, pass the organization's id to
            organization_purge, otherwise pass its name
        :type by_id: boolean
        :param is_org: if True create and purge an organization, if False a
            group
        :type is_org: boolean

        '''
        if is_org:
            group_or_org = self._organization_create(name)
        else:
            group_or_org = self._group_create(name)

        # Purge the group or organization.
        if is_org:
            action = 'organization_purge'
        else:
            action = 'group_purge'
        if by_id:
            identifier = group_or_org['id']
        else:
            identifier = group_or_org['name']
        result = tests.call_action_api(self.app, action, id=identifier,
                                       apikey=self.sysadmin.apikey,
                                       )
        assert result is None

        # Now trying to show the group or organization should give a 404.
        if is_org:
            action = 'organization_show'
        else:
            action = 'group_show'
        result = tests.call_action_api(self.app, action, id=name, status=404)
        assert result == {'__type': 'Not Found Error', 'message': 'Not found'}

        # The group or organization should not appear in group_list or
        # organization_list.
        if is_org:
            action = 'organization_list'
        else:
            action = 'group_list'
        assert name not in tests.call_action_api(self.app, action)

        # The package should no longer belong to the group or organization.
        package = tests.call_action_api(self.app, 'package_show',
                                        id=self.package['name'])
        if is_org:
            assert package['organization'] is None
        else:
            assert group_or_org['name'] not in [group_['name'] for group_
                                                in package['groups']]

        # TODO: Also want to assert that user is not in group or organization
        # anymore, but how to get a user's groups or organizations?

        # It should be possible to create a new group or organization with the
        # same name as the purged one (you would not be able to do this if you
        # had merely deleted the original group or organization).
        if is_org:
            action = 'organization_create'
        else:
            action = 'group_create'
        new_group_or_org = tests.call_action_api(self.app, action, name=name,
                                                 apikey=self.sysadmin.apikey,
                                                 )
        assert new_group_or_org['name'] == name

        # TODO: Should we do a model-level check, to check that the group or
        # org is really purged?

    def test_organization_purge_by_name(self):
        '''A sysadmin should be able to purge an organization by name.'''

        self._test_group_or_organization_purge('organization-to-be-purged',
                                               by_id=False, is_org=True)

    def test_group_purge_by_name(self):
        '''A sysadmin should be able to purge a group by name.'''
        self._test_group_or_organization_purge('group-to-be-purged',
                                               by_id=False, is_org=False)

    def test_organization_purge_by_id(self):
        '''A sysadmin should be able to purge an organization by id.'''
        self._test_group_or_organization_purge('organization-to-be-purged-2',
                                               by_id=True, is_org=True)

    def test_group_purge_by_id(self):
        '''A sysadmin should be able to purge a group by id.'''
        self._test_group_or_organization_purge('group-to-be-purged-2',
                                               by_id=True, is_org=False)

    def _test_group_or_org_purge_with_invalid_id(self, is_org):

        if is_org:
            action = 'organization_purge'
        else:
            action = 'group_purge'

        for name in ('foo', 'invalid name', None, ''):
            # Try to purge an organization, but pass an invalid name.
            result = tests.call_action_api(self.app, action,
                                           apikey=self.sysadmin.apikey,
                                           id=name,
                                           status=404,
                                           )
            if is_org:
                message = 'Not found: Organization was not found'
            else:
                message = 'Not found: Group was not found'
            assert result == {'__type': 'Not Found Error', 'message': message}

    def test_organization_purge_with_invalid_id(self):
        '''
        Trying to purge an organization with an invalid ID should give a 404.

        '''
        self._test_group_or_org_purge_with_invalid_id(is_org=True)

    def test_group_purge_with_invalid_id(self):
        '''Trying to purge a group with an invalid ID should give a 404.'''
        self._test_group_or_org_purge_with_invalid_id(is_org=False)

    def _test_group_or_org_purge_with_missing_id(self, is_org):
        if is_org:
            action = 'organization_purge'
        else:
            action = 'group_purge'
        result = tests.call_action_api(self.app, action,
                                       apikey=self.sysadmin.apikey,
                                       status=409,
                                       )
        assert result == {'__type': 'Validation Error',
                          'id': ['Missing value']}

    def test_organization_purge_with_missing_id(self):
        '''Trying to purge an organization without passing an id should give
        a 409.'''
        self._test_group_or_org_purge_with_missing_id(is_org=True)

    def test_group_purge_with_missing_id(self):
        '''Trying to purge a group without passing an id should give a 409.'''
        self._test_group_or_org_purge_with_missing_id(is_org=False)

    def _test_visitors_cannot_purge_groups_or_orgs(self, is_org):
        if is_org:
            group_or_org = self._organization_create('org-to-be-purged-3')
        else:
            group_or_org = self._group_create('group-to-be-purged-3')

        # Try to purge the group or organization without an API key.
        if is_org:
            action = 'organization_purge'
        else:
            action = 'group_purge'
        result = tests.call_action_api(self.app, action, id=group_or_org['id'],
                                       status=403,
                                       )
        assert result['__type'] == 'Authorization Error'

    def test_visitors_cannot_purge_organizations(self):
        '''Visitors (who aren't logged in) should not be authorized to purge
        organizations.

        '''
        self._test_visitors_cannot_purge_groups_or_orgs(is_org=True)

    def test_visitors_cannot_purge_groups(self):
        '''Visitors (who aren't logged in) should not be authorized to purge
        groups.

        '''
        self._test_visitors_cannot_purge_groups_or_orgs(is_org=False)

    def _test_users_cannot_purge_groups_or_orgs(self, is_org):
        if is_org:
            group_or_org = self._organization_create('org-to-be-purged-4')
        else:
            group_or_org = self._group_create('group-to-be-purged-4')

        # Try to purge the group or organization with a non-member's API key.
        if is_org:
            action = 'organization_purge'
        else:
            action = 'group_purge'
        result = tests.call_action_api(self.app, action, id=group_or_org['id'],
                                       apikey=self.visitor['apikey'],
                                       status=403,
                                       )
        assert result == {'__type': 'Authorization Error',
                          'message': 'Access denied'}

    def test_users_cannot_purge_organizations(self):
        '''Users who are not members of an organization should not be
        authorized to purge the organization.

        '''
        self._test_users_cannot_purge_groups_or_orgs(is_org=True)

    def test_users_cannot_purge_groups(self):
        '''Users who are not members of a group should not be authorized to
        purge the group.

        '''
        self._test_users_cannot_purge_groups_or_orgs(is_org=False)

    def _test_members_cannot_purge_groups_or_orgs(self, is_org):
        if is_org:
            group_or_org = self._organization_create('org-to-be-purged-5')
        else:
            group_or_org = self._group_create('group-to-be-purged-5')

        # Try to purge the organization with an organization member's API key.
        if is_org:
            action = 'organization_purge'
        else:
            action = 'group_purge'
        result = tests.call_action_api(self.app, action, id=group_or_org['id'],
                                       apikey=self.member['apikey'],
                                       status=403,
                                       )
        assert result == {'__type': 'Authorization Error',
                          'message': 'Access denied'}

    def test_members_cannot_purge_organizations(self):
        '''Members of an organization should not be authorized to purge the
        organization.

        '''
        self._test_members_cannot_purge_groups_or_orgs(is_org=True)

    def test_members_cannot_purge_groups(self):
        '''Members of a group should not be authorized to purge the group.

        '''
        self._test_members_cannot_purge_groups_or_orgs(is_org=False)

    def _test_editors_cannot_purge_groups_or_orgs(self, is_org):
        if is_org:
            group_or_org = self._organization_create('org-to-be-purged-6')
        else:
            group_or_org = self._group_create('group-to-be-purged-6')

        # Try to purge the group or organization with an editor's API key.
        if is_org:
            action = 'organization_purge'
        else:
            action = 'group_purge'
        result = tests.call_action_api(self.app, action, id=group_or_org['id'],
                                       apikey=self.editor['apikey'],
                                       status=403,
                                       )
        assert result == {'__type': 'Authorization Error',
                          'message': 'Access denied'}

    def test_editors_cannot_purge_organizations(self):
        '''Editors of an organization should not be authorized to purge the
        organization.

        '''
        self._test_editors_cannot_purge_groups_or_orgs(is_org=True)

    def test_editors_cannot_purge_groups(self):
        '''Editors of a group should not be authorized to purge the group.

        '''
        self._test_editors_cannot_purge_groups_or_orgs(is_org=False)

    def _test_admins_cannot_purge_groups_or_orgs(self, is_org):
        if is_org:
            group_or_org = self._organization_create('org-to-be-purged-7')
        else:
            group_or_org = self._group_create('group-to-be-purged-7')

        # Try to purge the group or organization with an admin's API key.
        if is_org:
            action = 'organization_purge'
        else:
            action = 'group_purge'
        result = tests.call_action_api(self.app, action,
                                       id=group_or_org['id'],
                                       apikey=self.admin['apikey'],
                                       status=403,
                                       )
        assert result == {'__type': 'Authorization Error',
                          'message': 'Access denied'}

    def test_admins_cannot_purge_organizations(self):
        '''Admins of an organization should not be authorized to purge the
        organization.

        '''
        self._test_admins_cannot_purge_groups_or_orgs(is_org=True)

    def test_admins_cannot_purge_groups(self):
        '''Admins of a group should not be authorized to purge the group.

        '''
        self._test_admins_cannot_purge_groups_or_orgs(is_org=False)
