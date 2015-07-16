from bs4 import BeautifulSoup
from nose.tools import assert_equal, assert_true
from routes import url_for

from ckan.tests import factories, helpers
from ckan.tests.helpers import webtest_submit, submit_and_follow, assert_in


class TestOrganizationNew(helpers.FunctionalTestBase):
    def setup(self):
        super(TestOrganizationNew, self).setup()
        self.app = helpers._get_test_app()
        self.user = factories.User()
        self.user_env = {'REMOTE_USER': self.user['name'].encode('ascii')}
        self.organization_new_url = url_for(controller='organization',
                                            action='new')

    def test_not_logged_in(self):
        self.app.get(url=url_for(controller='group', action='new'),
                     status=302)

    def test_name_required(self):
        response = self.app.get(url=self.organization_new_url,
                                extra_environ=self.user_env)
        form = response.forms['organization-edit-form']
        response = webtest_submit(form, name='save',
                                  extra_environ=self.user_env)

        assert_true('organization-edit-form' in response.forms)
        assert_true('Name: Missing value' in response)

    def test_saved(self):
        response = self.app.get(url=self.organization_new_url,
                                extra_environ=self.user_env)

        form = response.forms['organization-edit-form']
        form['name'] = u'saved'

        response = submit_and_follow(self.app, form, name='save',
                                     extra_environ=self.user_env)
        group = helpers.call_action('organization_show', id='saved')
        assert_equal(group['title'], u'')
        assert_equal(group['type'], 'organization')
        assert_equal(group['state'], 'active')

    def test_all_fields_saved(self):
        app = helpers._get_test_app()
        response = app.get(url=self.organization_new_url,
                           extra_environ=self.user_env)

        form = response.forms['organization-edit-form']
        form['name'] = u'all-fields-saved'
        form['title'] = 'Science'
        form['description'] = 'Sciencey datasets'
        form['image_url'] = 'http://example.com/image.png'

        response = submit_and_follow(self.app, form, name='save',
                                     extra_environ=self.user_env)
        group = helpers.call_action('organization_show', id='all-fields-saved')
        assert_equal(group['title'], u'Science')
        assert_equal(group['description'], 'Sciencey datasets')


class TestOrganizationRead(helpers.FunctionalTestBase):
    def setup(self):
        super(TestOrganizationRead, self).setup()
        self.app = helpers._get_test_app()
        self.user = factories.User()
        self.user_env = {'REMOTE_USER': self.user['name'].encode('ascii')}
        self.organization = factories.Organization(user=self.user)

    def test_organization_read(self):
        response = self.app.get(url=url_for(controller='organization',
                                            action='read',
                                            id=self.organization['id']),
                                status=200,
                                extra_environ=self.user_env)
        assert_in(self.organization['title'], response)
        assert_in(self.organization['description'], response)


class TestOrganizationEdit(helpers.FunctionalTestBase):
    def setup(self):
        super(TestOrganizationEdit, self).setup()
        self.app = helpers._get_test_app()
        self.user = factories.User()
        self.user_env = {'REMOTE_USER': self.user['name'].encode('ascii')}
        self.organization = factories.Organization(user=self.user)
        self.organization_edit_url = url_for(controller='organization',
                                             action='edit',
                                             id=self.organization['id'])

    def test_group_doesnt_exist(self):
        url = url_for(controller='organization',
                      action='edit',
                      id='doesnt_exist')
        self.app.get(url=url, extra_environ=self.user_env,
                     status=404)

    def test_saved(self):
        response = self.app.get(url=self.organization_edit_url,
                                extra_environ=self.user_env)

        form = response.forms['organization-edit-form']
        response = webtest_submit(form, name='save',
                                  extra_environ=self.user_env)
        group = helpers.call_action('organization_show',
                                    id=self.organization['id'])
        assert_equal(group['title'], u'Test Organization')
        assert_equal(group['type'], 'organization')
        assert_equal(group['state'], 'active')

    def test_all_fields_saved(self):
        response = self.app.get(url=self.organization_edit_url,
                                extra_environ=self.user_env)

        form = response.forms['organization-edit-form']
        form['name'] = u'all-fields-edited'
        form['title'] = 'Science'
        form['description'] = 'Sciencey datasets'
        form['image_url'] = 'http://example.com/image.png'
        response = webtest_submit(form, name='save',
                                  extra_environ=self.user_env)

        group = helpers.call_action('organization_show',
                                    id=self.organization['id'])
        assert_equal(group['title'], u'Science')
        assert_equal(group['description'], 'Sciencey datasets')
        assert_equal(group['image_url'], 'http://example.com/image.png')


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


class TestOrganizationBulkProcess(helpers.FunctionalTestBase):
    def setup(self):
        super(TestOrganizationBulkProcess, self).setup()
        self.app = helpers._get_test_app()
        self.user = factories.User()
        self.user_env = {'REMOTE_USER': self.user['name'].encode('ascii')}
        self.organization = factories.Organization(user=self.user)
        self.organization_bulk_url = url_for(controller='organization',
                                             action='bulk_process',
                                             id=self.organization['id'])

    def test_make_private(self):
        datasets = [factories.Dataset(owner_org=self.organization['id'])
                    for i in range(0, 5)]
        response = self.app.get(url=self.organization_bulk_url,
                                extra_environ=self.user_env)
        form = response.forms[1]
        for v in form.fields.values():
            try:
                v[0].checked = True
            except AttributeError:
                pass
        response = webtest_submit(form, name='bulk_action.private',
                                  value='private',
                                  extra_environ=self.user_env)

        for dataset in datasets:
            d = helpers.call_action('package_show', id=dataset['id'])
            assert_equal(d['private'], True)

    def test_make_public(self):
        datasets = [factories.Dataset(owner_org=self.organization['id'],
                                      private=True)
                    for i in range(0, 5)]
        response = self.app.get(url=self.organization_bulk_url,
                                extra_environ=self.user_env)
        form = response.forms[1]
        for v in form.fields.values():
            try:
                v[0].checked = True
            except AttributeError:
                pass
        response = webtest_submit(form, name='bulk_action.public',
                                  value='public',
                                  extra_environ=self.user_env)

        for dataset in datasets:
            d = helpers.call_action('package_show', id=dataset['id'])
            assert_equal(d['private'], False)

    def test_delete(self):
        datasets = [factories.Dataset(owner_org=self.organization['id'],
                                      private=True)
                    for i in range(0, 5)]
        response = self.app.get(url=self.organization_bulk_url,
                                extra_environ=self.user_env)
        form = response.forms[1]
        for v in form.fields.values():
            try:
                v[0].checked = True
            except AttributeError:
                pass
        response = webtest_submit(form, name='bulk_action.delete',
                                  value='delete',
                                  extra_environ=self.user_env)

        for dataset in datasets:
            d = helpers.call_action('package_show', id=dataset['id'])
            assert_equal(d['state'], 'deleted')


class TestOrganizationSearch(helpers.FunctionalTestBase):

    def test_organization_search(self):
        '''Requesting organization search (index) returns list of
        organizations and search form.'''
        app = self._get_test_app()
        factories.Organization(name='org-one', title='Org One')
        factories.Organization(name='org-two', title='Org Two')
        factories.Organization(name='org-three', title='Org Three')

        search_url = url_for(controller='organization', action='index')
        index_response = app.get(search_url)
        index_response_html = BeautifulSoup(index_response.body)
        org_names = index_response_html.select('ul.media-grid '
                                               'li.media-item '
                                               'h3.media-heading')
        org_names = [n.string for n in org_names]

        assert_equal(len(org_names), 3)
        assert_true('Org One' in org_names)
        assert_true('Org Two' in org_names)
        assert_true('Org Three' in org_names)

    def test_organization_search_results(self):
        '''Searching via organization search form returns list of expected
        organizations.'''
        app = self._get_test_app()
        factories.Organization(name='org-one', title='AOrg One')
        factories.Organization(name='org-two', title='AOrg Two')
        factories.Organization(name='org-three', title='Org Three')

        search_url = url_for(controller='organization', action='index')
        index_response = app.get(search_url)
        search_form = index_response.forms['organization-search-form']
        search_form['q'] = 'AOrg'
        search_response = webtest_submit(search_form)

        search_response_html = BeautifulSoup(search_response.body)
        org_names = search_response_html.select('ul.media-grid '
                                                'li.media-item '
                                                'h3.media-heading')
        org_names = [n.string for n in org_names]

        assert_equal(len(org_names), 2)
        assert_true('AOrg One' in org_names)
        assert_true('AOrg Two' in org_names)
        assert_true('Org Three' not in org_names)

    def test_organization_search_no_results(self):
        '''Searching with a term that doesn't apply returns no results.'''
        app = self._get_test_app()
        factories.Organization(name='org-one', title='AOrg One')
        factories.Organization(name='org-two', title='AOrg Two')
        factories.Organization(name='org-three', title='Org Three')

        search_url = url_for(controller='organization', action='index')
        index_response = app.get(search_url)
        search_form = index_response.forms['organization-search-form']
        search_form['q'] = 'No Results Here'
        search_response = webtest_submit(search_form)

        search_response_html = BeautifulSoup(search_response.body)
        org_names = search_response_html.select('ul.media-grid '
                                                'li.media-item '
                                                'h3.media-heading')
        org_names = [n.string for n in org_names]

        assert_equal(len(org_names), 0)
        assert_true("No organizations found for &#34;No Results Here&#34;"
                    in search_response)
