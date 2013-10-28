'''Tests for the ckanext.example_iauthfunctions extension.

'''
import paste.fixture
import pylons.test

import ckan.model as model
import ckan.tests as tests
import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit


class TestExampleIAuthFunctionsPlugin(object):
    '''Tests for the ckanext.example_iauthfunctions.plugin module.

    '''
    @classmethod
    def setup_class(cls):
        '''Nose runs this method once to setup our test class.'''

        # Make the Paste TestApp that we'll use to simulate HTTP requests to
        # CKAN.
        cls.app = paste.fixture.TestApp(pylons.test.pylonsapp)

        # Test code should use CKAN's plugins.load() function to load plugins
        # to be tested.
        plugins.load('example_iauthfunctions')

    def setup(self):
        '''Nose runs this method before each test method in our test class.'''

        # Access CKAN's model directly (bad) to create a sysadmin user and save
        # it against self for all test methods to access.
        self.sysadmin = model.User(name='test_sysadmin', sysadmin=True)
        model.Session.add(self.sysadmin)
        model.Session.commit()
        model.Session.remove()

    def teardown(self):
        '''Nose runs this method after each test method in our test class.'''

        # Rebuild CKAN's database after each test method, so that each test
        # method runs with a clean slate.
        model.repo.rebuild_db()

    @classmethod
    def teardown_class(cls):
        '''Nose runs this method once after all the test methods in our class
        have been run.

        '''
        # We have to unload the plugin we loaded, so it doesn't affect any
        # tests that run after ours.
        plugins.unload('example_iauthfunctions')

    def _make_curators_group(self):
        '''This is a helper method for test methods to call when they want
        the 'curators' group to be created.

        '''
        # Create a user who will *not* be a member of the curators group.
        noncurator = tests.call_action_api(self.app, 'user_create',
                                           apikey=self.sysadmin.apikey,
                                           name='noncurator',
                                           email='email',
                                           password='password')

        # Create a user who will be a member of the curators group.
        curator = tests.call_action_api(self.app, 'user_create',
                                        apikey=self.sysadmin.apikey,
                                        name='curator',
                                        email='email',
                                        password='password')

        # Create the curators group, with the 'curator' user as a member.
        users = [{'name': curator['name'], 'capacity': 'member'}]
        curators_group = tests.call_action_api(self.app, 'group_create',
                                               apikey=self.sysadmin.apikey,
                                               name='curators',
                                               users=users)

        return (noncurator, curator, curators_group)

    def test_group_create_with_no_curators_group(self):
        '''Test that group_create doesn't crash when there's no curators group.

        '''
        # Make sure there's no curators group.
        assert 'curators' not in tests.call_action_api(self.app, 'group_list')

        # Make our sysadmin user create a group. CKAN should not crash.
        tests.call_action_api(self.app, 'group_create', name='test-group',
                              apikey=self.sysadmin.apikey)

    def test_group_create_with_visitor(self):
        '''A visitor (not logged in) should not be able to create a group.

        Note: this also tests that the group_create auth function doesn't
        crash when the user isn't logged in.

        '''
        noncurator, curator, curators_group = self._make_curators_group()
        result = tests.call_action_api(self.app, 'group_create',
                                       name='this_group_should_not_be_created',
                                       status=403)
        assert result['__type'] == 'Authorization Error'

    def test_group_create_with_non_curator(self):
        '''A user who isn't a member of the curators group should not be able
        to create a group.

        '''
        noncurator, curator, curators_group = self._make_curators_group()
        result = tests.call_action_api(self.app, 'group_create',
                                       name='this_group_should_not_be_created',
                                       apikey=noncurator['apikey'],
                                       status=403)
        assert result['__type'] == 'Authorization Error'

    def test_group_create_with_curator(self):
        '''A member of the curators group should be able to create a group.

        '''
        noncurator, curator, curators_group = self._make_curators_group()
        name = 'my-new-group'
        result = tests.call_action_api(self.app, 'group_create',
                                       name=name,
                                       apikey=curator['apikey'])
        assert result['name'] == name


class TestExampleIAuthFunctionsPluginV3(TestExampleIAuthFunctionsPlugin):
    '''Tests for the ckanext.example_iauthfunctions.plugin_v3 module.

    '''
    @classmethod
    def setup_class(cls):
        cls.app = paste.fixture.TestApp(pylons.test.pylonsapp)
        plugins.load('example_iauthfunctions_v3')

    @classmethod
    def teardown_class(cls):
        plugins.unload('example_iauthfunctions_v3')

    def test_group_create_with_no_curators_group(self):
        '''Test that group_create returns a 404 when there's no curators group.

        With this version of the plugin group_create returns a spurious 404
        when a user _is_ logged-in but the site has no curators group.

        '''
        assert 'curators' not in tests.call_action_api(self.app, 'group_list')
        user = tests.call_action_api(self.app, 'user_create',
                                     apikey=self.sysadmin.apikey,
                                     name='test-user',
                                     email='email',
                                     password='password')
        response = tests.call_action_api(self.app, 'group_create',
                                         name='test_group',
                                         apikey=user['apikey'], status=404)
        assert response == {'__type': 'Not Found Error',
                            'message': 'Not found'}

    def test_group_create_with_visitor(self):
        '''Test that group_create returns 403 when no one is logged in.

        Since #1210 non-logged in requests are automatically rejected, unless
        the auth function has the appropiate decorator
        '''

        noncurator, curator, curators_group = self._make_curators_group()
        response = tests.call_action_api(self.app, 'group_create',
                                         name='this_group_shouldnt_be_created',
                                         status=403)
        assert response['__type'] == 'Authorization Error'


class TestExampleIAuthFunctionsPluginV2(TestExampleIAuthFunctionsPlugin):
    '''Tests for the ckanext.example_iauthfunctions.plugin_v2 module.

    '''
    @classmethod
    def setup_class(cls):
        cls.app = paste.fixture.TestApp(pylons.test.pylonsapp)
        plugins.load('example_iauthfunctions_v2')

    @classmethod
    def teardown_class(cls):
        plugins.unload('example_iauthfunctions_v2')

    def test_group_create_with_curator(self):
        '''Test that a curator can*not* create a group.

        In this version of the plugin, even users who are members of the
        curators group cannot create groups.

        '''
        noncurator, curator, curators_group = self._make_curators_group()
        result = tests.call_action_api(self.app, 'group_create',
                                       name='this_group_should_not_be_created',
                                       apikey=curator['apikey'],
                                       status=403)
        assert result['__type'] == 'Authorization Error'
