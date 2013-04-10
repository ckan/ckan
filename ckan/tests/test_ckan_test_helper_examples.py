# These are some example tests using the CkanTestHelper. If the
# CkanTestHelper is accepted then I will also look at getting most of these
# tests accepted too.  The tests demonstrate both backend and web front end
# testing.
#
# NOTE: CkanTestHelper is the only external item directly accessed by the
# tests.

import ckan_test_helper
t = ckan_test_helper.CkanTestHelper()


class TestUserLogin(object):
    ''' Basic testing of frontend with a user. '''

    @classmethod
    def setup_class(cls):
        t.create_user(name='test_user', password='pass')
        t.create_user(name='moo')
        # Use the new templates yeah!
        t.config_update({'ckan.legacy_templates': 'no'})

    @classmethod
    def teardown_class(cls):
        t.reset_db()
        t.config_reset()

    def test_register(self):
        # try to register a user via the web front end
        r = t.get_url(controller='user', action='register')
        f = r.forms[1]

        # name missing
        r = f.submit('save')
        errors = r.pyquery('.error-explanation li').text()
        assert 'Name: Missing value' in errors

        # name registered
        f['name'] = 'moo'
        r = f.submit('save')
        errors = r.pyquery('.error-explanation li').text()
        assert 'Name: That login name is not available.' in errors

        assert 'Email: Missing value' in errors

        # Any email will do even non-valid ones
        f['email'] = 'moo@moo.moo'
        r = f.submit('save')
        errors = r.pyquery('.error-explanation li').text()
        assert 'Email: Missing value' not in errors

        # password missing non-matching etc
        assert 'Please enter both passwords' in errors
        f['password1'] = 'secret'
        r = f.submit('save')
        errors = r.pyquery('.error-explanation li').text()
        assert 'The passwords you entered do not match' in errors
        f['password1'] = ''
        f['password2'] = 'secret'
        errors = r.pyquery('.error-explanation li').text()
        assert 'The passwords you entered do not match' in errors

        # correct data
        f['password1'] = 'secret'
        f['name'] = 'moop'
        f['fullname'] = 'moop user'
        r = f.submit('save')
        r = t.auto_follow(r)

        # we should register and get to our dashboard
        t.assert_location(r, controller='user', action='dashboard')

        # check data correct
        userobj = r.c.userobj
        assert userobj.name == 'moop'
        assert userobj.fullname == 'moop user'
        assert userobj.email == 'moo@moo.moo'

        # log in to check our password is set correctly
        t.logout()
        r = t.get_url(controller='user', action='login')
        f = r.forms[1]
        f['login'] = 'moop'
        f['password'] = 'secret'
        r = f.submit()
        r = t.auto_follow(r)
        assert r.c.user == 'moop'

        # all good so log out
        t.logout()

    def _test_login(self):
        # if no user given we redirect to login
        r = t.get_url(controller='user', action='dashboard', status=302)
        # we should be redirected to the login form
        r = t.auto_follow(r)
        t.assert_location(r, controller='user', action='login')

        # login with incorrect credentials
        f = r.forms[1]
        f['login'] = 'test_user'
        f['password'] = 'wrong_pass'
        r = f.submit()

        # Check our error message
        r = t.auto_follow(r)
        assert 'Login failed' in r.pyquery('.error-explanation li').text()

        # login with correct credentials
        f = r.forms[1]
        f['login'] = 'test_user'
        f['password'] = 'pass'
        r = f.submit()

        r = t.auto_follow(r)
        t.assert_location(r, controller='user', action='dashboard')
        assert r.pyquery('span.username').text() == 'test_user'

        # now logout
        r = t.get_url(controller='user', action='logout')
        t.auto_follow(r)

        # dashboard no longer available
        t.get_url(controller='user', action='dashboard', status=302)

    def _test_helper_login_functionality(self):
        # Test CkanTestHelper login/out functionality we must be logged in
        # to see the dashboard.
        t.get_url(controller='user', action='dashboard', status=302)
        t.login('test_user')
        r = t.get_url(controller='user', action='dashboard', status=200)
        assert r.c.user == 'test_user'
        t.logout()
        t.get_url(controller='user', action='dashboard', status=302)
        # login and out as a different user
        t.login('moo')
        assert r.c.user == 'moo'
        t.logout()


class TestGroup(object):
    ''' This tests adding and removing a group from a dataset.  Mainly it is
    here as this is a test I needed to write. '''

    @classmethod
    def setup_class(cls):
        t.create_user(name='test_ds_owner')
        t.create_user(name='test_non_ds_owner')
        t.create_org(name='org', user='test_ds_owner')
        t.create_group(name='group1', user='test_ds_owner')
        t.create_group(name='group2', user='test_non_ds_owner')
        t.create_dataset(name='dataset', org='org', user='test_ds_owner')

    @classmethod
    def teardown_class(cls):
        t.reset_db()

    def test_add_remove_group(self):
        ds = t.api_action('package_show', {'id': t.dataset('dataset')['id']})
        assert ds['groups'] == []
        ds['groups'] = [{'id': t.group('group1')['id']}]
        ds = t.api_action('package_update', ds, user='test_ds_owner')
        group_ids = t.list_dict_reduce(ds['groups'], 'id')
        assert group_ids == [t.group('group1')['id']]
        ds['groups'] = []
        ds = t.api_action('package_update', ds, user='test_ds_owner')
        assert ds['groups'] == []

        ds['groups'] = [{'id': t.group('group2')['id']}]
        ds = t.api_action('package_update',
                          ds, user='test_ds_owner', status=403)
        ds = t.api_action('package_show', {'id': t.dataset('dataset')['id']})
        assert ds['groups'] == []


class TestRelatedItemDeletePermissions(object):
    ''' This tests the permissions for deleting a related item. '''

    @classmethod
    def setup_class(cls):
        t.create_user(name='test_visitor')
        t.create_user(name='test_org_owner')
        t.create_user(name='test_org_member')
        t.create_user(name='test_org_editor')
        t.create_user(name='test_item_owner')
        t.create_org(name='org', user='test_org_owner')
        t.add_org_role('org', 'test_org_member', 'member')
        t.add_org_role('org', 'test_org_editor', 'editor')
        ds = t.create_dataset(name='dataset', owner_org='org',
                              user='test_org_owner')
        t.create_related(title='rel1', dataset_id=ds['id'],
                         user='test_org_owner')
        t.create_related(title='rel2', dataset_id=ds['id'],
                         user='test_org_owner')
        t.create_related(title='rel3', dataset_id=ds['id'],
                         user='test_org_owner')
        t.create_related(title='rel4', dataset_id=ds['id'],
                         user='test_org_owner')
        t.create_related(title='rel5', dataset_id=ds['id'],
                         user='test_org_owner')
        t.create_related(title='rel_no_dataset1', user='test_item_owner')
        t.create_related(title='rel_no_dataset2', user='test_item_owner')
        t.create_related(title='rel_no_dataset3', user='test_item_owner')

    @classmethod
    def teardown_class(cls):
        t.reset_db()

    def test_visitor_cannot_delete_related_item(self):
        t.api_action('related_delete',
                     t.related('rel1'),
                     user='test_visitor',
                     status=403)

    def test_dataset_owner_can_delete_related_item(self):
        t.api_action('related_delete',
                     t.related('rel2'),
                     user='test_org_owner',
                     status=200)

    def test_item_owner_can_delete_related_item(self):
        t.api_action('related_delete',
                     t.related('rel_no_dataset1'),
                     user='test_item_owner',
                     status=200)

    def test_others_cannot_delete_related_item(self):
        t.api_action('related_delete',
                     t.related('rel_no_dataset2'),
                     user='test_visitor',
                     status=403)

    def test_sysadmin_can_delete_related_item(self):
        t.api_action('related_delete',
                     t.related('rel3'),
                     user='test_sysadmin',
                     status=200)
        t.api_action('related_delete',
                     t.related('rel_no_dataset3'),
                     user='test_sysadmin',
                     status=200)

    def test_organization_member_cannot_delete_related_item(self):
        t.api_action('related_delete',
                     t.related('rel4'),
                     user='test_org_member',
                     status=403)

    def test_organization_editor_can_delete_related_item(self):
        t.api_action('related_delete',
                     t.related('rel5'),
                     user='test_org_owner',
                     status=200)


class TestConfig(object):
    ''' This demonstrates how the config can be changed during a test using
    the CkanTestHelper.  Currently a plugin is loaded via the config.  When
    branch 547-plugins-love is merged then plugin_load() and plugin_unload()
    methods will be added to the helper to make adding/removing plugins
    simpler. '''

    def test(self):
        # change to new templates
        t.config_update({'ckan.legacy_templates': 'no'})
        # check the helper not there
        response = t.get_url(controller='home', action='index')
        assert not response.html.find('span', {'class': 'example_itemplate'})
        # add plugin and test
        t.config_update({'ckan.plugins': 'example_itemplatehelpers'})
        response = t.get_url(controller='home', action='index')
        # via beautiful soup
        assert response.html.find('span', {'class': 'example_itemplate'})
        # via pyquery
        assert response.pyquery('.example_itemplate')
        # reset stuff
        t.config_reset()
        # should all be gone
        t.config_update({'ckan.legacy_templates': 'no'})
        response = t.get_url(controller='home', action='index')
        assert not response.pyquery('.example_itemplate')
        t.config_reset()
