from nose.tools import assert_equal
from routes import url_for

from ckan.tests import factories, helpers
from ckan.tests.helpers import submit_and_follow


class TestOrganizationDelete(helpers.FunctionalTestBase):
    def setup(self):
        super(TestOrganizationDelete, self).setup()
        self.app = helpers._get_test_app()
        self.user = factories.User()
        self.user_env = {'REMOTE_USER': self.user['name'].encode('ascii')}
        self.organization = factories.Organization(user=self.user)

    def test_owner_delete(self):
        response = self.app.get(url=url_for(controller='organization',
                                            action='delete',
                                            id=self.organization['id']),
                                status=200,
                                extra_environ=self.user_env)

        form = response.forms['organization-confirm-delete-form']
        response = submit_and_follow(self.app, form, name='delete',
                                     extra_environ=self.user_env)
        organization = helpers.call_action('organization_show',
                                           id=self.organization['id'])
        assert_equal(organization['state'], 'deleted')

    def test_sysadmin_delete(self):
        sysadmin = factories.Sysadmin()
        extra_environ = {'REMOTE_USER': sysadmin['name'].encode('ascii')}
        response = self.app.get(url=url_for(controller='organization',
                                            action='delete',
                                            id=self.organization['id']),
                                status=200,
                                extra_environ=extra_environ)

        form = response.forms['organization-confirm-delete-form']
        response = submit_and_follow(self.app, form, name='delete',
                                     extra_environ=self.user_env)
        organization = helpers.call_action('organization_show',
                                           id=self.organization['id'])
        assert_equal(organization['state'], 'deleted')

    def test_non_authorized_user_trying_to_delete_fails(self):
        user = factories.User()
        extra_environ = {'REMOTE_USER': user['name'].encode('ascii')}
        self.app.get(url=url_for(controller='organization',
                                 action='delete',
                                 id=self.organization['id']),
                     status=401,
                     extra_environ=extra_environ)

        organization = helpers.call_action('organization_show',
                                           id=self.organization['id'])
        assert_equal(organization['state'], 'active')

    def test_anon_user_trying_to_delete_fails(self):
        self.app.get(url=url_for(controller='organization',
                                 action='delete',
                                 id=self.organization['id']),
                     status=302)  # redirects to login form

        organization = helpers.call_action('organization_show',
                                           id=self.organization['id'])
        assert_equal(organization['state'], 'active')
