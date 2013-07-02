'''Functional tests for the organizations-related APIs.

'''
import ckan.model as model
import ckan.logic as logic

import paste
import pylons.test
import ckanapi
import nose.tools


class TestOrganizationPurging(object):
    '''Tests for the organization_purge API.

    '''
    @classmethod
    def setup_class(cls):
        cls.app = paste.fixture.TestApp(pylons.test.pylonsapp)
        cls.api = ckanapi.TestAppCKAN(cls.app)

        # Make a sysadmin user.
        cls.sysadmin = model.User(name='test_sysadmin', sysadmin=True)
        model.Session.add(cls.sysadmin)
        model.Session.commit()
        model.Session.remove()

        # A package that will be added to our test organizations.
        cls.package = cls.api.action.package_create(name='org_package',
                                                    apikey=cls.sysadmin.apikey)

        # A user who will not be a member of our test organizations.
        cls.org_visitor = cls.api.action.user_create(name='non_member',
                                                     email='blah',
                                                     password='farm',
                                                    apikey=cls.sysadmin.apikey)

        # A user who will become a member of our test organizations.
        cls.org_member = cls.api.action.user_create(name='member',
                                                    email='blah',
                                                    password='farm',
                                                    apikey=cls.sysadmin.apikey)

        # A user who will become an editor of our test organizations.
        cls.org_editor = cls.api.action.user_create(name='editor',
                                                    email='blah',
                                                    password='farm',
                                                    apikey=cls.sysadmin.apikey)

        # A user who will become an admin of our test organizations.
        cls.org_admin = cls.api.action.user_create(name='admin',
                                                   email='blah',
                                                   password='farm',
                                                   apikey=cls.sysadmin.apikey)

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()

    def _organization_create(self, organization_name):
        '''Make an organization with a user and a dataset.'''

        # Make an organization with a user.
        organization = self.api.action.organization_create(
                                             apikey=self.sysadmin.apikey,
                                             name=organization_name,
                                             users=[
                                              {'name': self.org_member['name'],
                                               'capacity': 'member',
                                               },
                                              {'name': self.org_editor['name'],
                                               'capacity': 'editor',
                                               },
                                              {'name': self.org_admin['name'],
                                               'capacity': 'admin',
                                               }]
                                             )

        # Add a dataset to the organization (have to do this separately
        # because the packages param of organization_create doesn't work).
        self.api.action.package_update(name=self.package['name'],
                                       owner_org=organization['name'],
                                       apikey=self.sysadmin.apikey)

        # Let's just make sure that worked.
        package = self.api.action.package_show(id=self.package['id'])
        assert package['organization']['name'] == organization['name']
        organization = self.api.action.organization_show(id=organization['id'])
        assert self.package['name'] in [package_['name']
                                        for package_ in
                                        organization['packages']]
        assert self.org_visitor['name'] not in [user['name']
                                             for user in organization['users']]
        assert self.org_member['name'] in [user['name']
                                           for user in organization['users']
                                           if user['capacity'] == 'member']
        assert self.org_editor['name'] in [user['name']
                                           for user in organization['users']
                                           if user['capacity'] == 'editor']
        assert self.org_admin['name'] in [user['name']
                                          for user in organization['users']
                                          if user['capacity'] == 'admin']

        return organization

    def _test_organization_purge(self, org_name, by_id):
        '''Create an organization with the given name, and test purging it.

        :param name: the name of the organization to create and purge
        :param by_id: if True, pass the organization's id to
            organization_purge, otherwise pass its name
        :type by_id: boolean

        '''
        organization = self._organization_create(org_name)

        # Purge the organization.
        if by_id:
            result = self.api.action.organization_purge(
                                                   apikey=self.sysadmin.apikey,
                                                   id=organization['id'],
                                                   )
        else:
            result = self.api.action.organization_purge(
                                                   apikey=self.sysadmin.apikey,
                                                   id=organization['name'],
                                                   )
        assert result is None

        # Now trying to show the organization should give a 404.
        with nose.tools.assert_raises(logic.NotFound) as context:
            self.api.action.organization_show(id=org_name)
        assert context.exception.extra_msg == 'Not found'

        # The organization should not appear in organization_list.
        assert org_name not in self.api.action.organization_list()

        # The package should no longer belong to the organization.
        package = self.api.action.package_show(id=self.package['name'])
        assert package['organization'] is None

        # TODO: Also want to assert that user is not in organization anymore,
        # but how to get a user's organizations?

        # It should be possible to create a new organization with the same
        # name as the purged one (you would not be able to do this if you had
        # merely deleted the original organization).
        new_org = self.api.action.organization_create(name=org_name,
                                                   apikey=self.sysadmin.apikey,
                                                   )
        assert new_org['name'] == org_name

        # TODO: Should we do a model-level check, to check that the org is
        # really purged?

    def test_organization_purge_by_name(self):
        self._test_organization_purge('organization-to-be-purged', by_id=False)

    def test_organization_purge_by_id(self):
        self._test_organization_purge('organization-to-be-purged-2',
                                      by_id=True)

    def test_organization_purge_with_invalid_id(self):

        for name in ('foo', 'invalid name', None, ''):
            # Try to purge an organization, but pass an invalid name.
            with nose.tools.assert_raises(logic.NotFound) as context:
                self.api.action.organization_purge(id=name,
                                                   apikey=self.sysadmin.apikey)
            assert context.exception.extra_msg == 'Organization was not found'

    def test_organization_purge_with_missing_id(self):
        with nose.tools.assert_raises(logic.ValidationError) as context:
            self.api.action.organization_purge(apikey=self.sysadmin.apikey)
        assert context.exception.error_dict == {'__type': 'Validation Error',
                                                'id': ['Missing value']}

    def test_visitors_cannot_purge_organizations(self):
        '''Visitors (who aren't logged in) should not be authorized to purge
        organizations.

        '''
        organization = self._organization_create('organization-to-be-purged-3')

        # Try to purge the organization without an API key.
        with nose.tools.assert_raises(logic.NotAuthorized) as context:
            self.api.action.organization_purge(id=organization['id'])
        assert context.exception.extra_msg == {'__type': 'Authorization Error',
                                               'message': 'Access denied'}

    def test_users_cannot_purge_organizations(self):
        '''Users who are not members of an organization should not be
        authorized to purge the organization.

        '''
        organization = self._organization_create('organization-to-be-purged-4')

        # Try to purge the organization with a non-member's API key.
        with nose.tools.assert_raises(logic.NotAuthorized) as context:
            self.api.action.organization_purge(id=organization['id'],
                                             apikey=self.org_visitor['apikey'],
                                               )
        assert context.exception.extra_msg == {'__type': 'Authorization Error',
                                               'message': 'Access denied'}

    def test_members_cannot_purge_organizations(self):
        '''Members of an organization should not be authorized to purge the
        organization.

        '''
        organization = self._organization_create('organization-to-be-purged-5')

        # Try to purge the organization with an organization member's API key.
        with nose.tools.assert_raises(logic.NotAuthorized) as context:
            self.api.action.organization_purge(id=organization['id'],
                                              apikey=self.org_member['apikey'],
                                               )
        assert context.exception.extra_msg == {'__type': 'Authorization Error',
                                               'message': 'Access denied'}

    def test_editors_cannot_purge_organizations(self):
        '''Editors of an organization should not be authorized to purge the
        organization.

        '''
        organization = self._organization_create('organization-to-be-purged-6')

        # Try to purge the organization with an editor's API key.
        with nose.tools.assert_raises(logic.NotAuthorized) as context:
            self.api.action.organization_purge(id=organization['id'],
                                              apikey=self.org_editor['apikey'],
                                               )
        assert context.exception.extra_msg == {'__type': 'Authorization Error',
                                               'message': 'Access denied'}

    def test_admins_cannot_purge_organizations(self):
        '''Admins of an organization should not be authorized to purge the
        organization.

        '''
        organization = self._organization_create('organization-to-be-purged-7')

        # Try to purge the organization with an admin's API key.
        with nose.tools.assert_raises(logic.NotAuthorized) as context:
            self.api.action.organization_purge(id=organization['id'],
                                               apikey=self.org_admin['apikey'],
                                               )
        assert context.exception.extra_msg == {'__type': 'Authorization Error',
                                               'message': u'Access denied'}
