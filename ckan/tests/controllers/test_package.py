from bs4 import BeautifulSoup
from nose.tools import (
    assert_equal,
    assert_not_equal,
    assert_raises,
    assert_true,
)


from routes import url_for

import ckan.model as model
import ckan.plugins as p

import ckan.tests.helpers as helpers
import ckan.tests.factories as factories


webtest_submit = helpers.webtest_submit
submit_and_follow = helpers.submit_and_follow


def _get_package_new_page(app):
    user = factories.User()
    env = {'REMOTE_USER': user['name'].encode('ascii')}
    response = app.get(
        url=url_for(controller='package', action='new'),
        extra_environ=env,
    )
    return env, response


class TestPackageControllerNew(helpers.FunctionalTestBase):
    def test_form_renders(self):
        app = self._get_test_app()
        env, response = _get_package_new_page(app)
        assert_true('dataset-edit' in response.forms)

    def test_name_required(self):
        app = self._get_test_app()
        env, response = _get_package_new_page(app)
        form = response.forms['dataset-edit']

        response = webtest_submit(form, 'save', status=200, extra_environ=env)
        assert_true('dataset-edit' in response.forms)
        assert_true('Name: Missing value' in response)

    def test_resource_form_renders(self):
        app = self._get_test_app()
        env, response = _get_package_new_page(app)
        form = response.forms['dataset-edit']
        form['name'] = u'resource-form-renders'

        response = submit_and_follow(app, form, env, 'save')
        assert_true('resource-edit' in response.forms)

    def test_first_page_creates_draft_package(self):
        app = self._get_test_app()
        env, response = _get_package_new_page(app)
        form = response.forms['dataset-edit']
        form['name'] = u'first-page-creates-draft'

        webtest_submit(form, 'save', status=302, extra_environ=env)
        pkg = model.Package.by_name(u'first-page-creates-draft')
        assert_equal(pkg.state, 'draft')

    def test_resource_required(self):
        app = self._get_test_app()
        env, response = _get_package_new_page(app)
        form = response.forms['dataset-edit']
        form['name'] = u'one-resource-required'

        response = submit_and_follow(app, form, env, 'save')
        form = response.forms['resource-edit']

        response = webtest_submit(form, 'save', value='go-metadata',
                                  status=200, extra_environ=env)
        assert_true('resource-edit' in response.forms)
        assert_true('You must add at least one data resource' in response)

    def test_complete_package_with_one_resource(self):
        app = self._get_test_app()
        env, response = _get_package_new_page(app)
        form = response.forms['dataset-edit']
        form['name'] = u'complete-package-with-one-resource'

        response = submit_and_follow(app, form, env, 'save')
        form = response.forms['resource-edit']
        form['url'] = u'http://example.com/resource'

        submit_and_follow(app, form, env, 'save', 'go-metadata')
        pkg = model.Package.by_name(u'complete-package-with-one-resource')
        assert_equal(pkg.resources[0].url, u'http://example.com/resource')
        assert_equal(pkg.state, 'active')

    def test_complete_package_with_two_resources(self):
        app = self._get_test_app()
        env, response = _get_package_new_page(app)
        form = response.forms['dataset-edit']
        form['name'] = u'complete-package-with-two-resources'

        response = submit_and_follow(app, form, env, 'save')
        form = response.forms['resource-edit']
        form['url'] = u'http://example.com/resource0'

        response = submit_and_follow(app, form, env, 'save', 'again')
        form = response.forms['resource-edit']
        form['url'] = u'http://example.com/resource1'

        submit_and_follow(app, form, env, 'save', 'go-metadata')
        pkg = model.Package.by_name(u'complete-package-with-two-resources')
        assert_equal(pkg.resources[0].url, u'http://example.com/resource0')
        assert_equal(pkg.resources[1].url, u'http://example.com/resource1')
        assert_equal(pkg.state, 'active')

    def test_previous_button_works(self):
        app = self._get_test_app()
        env, response = _get_package_new_page(app)
        form = response.forms['dataset-edit']
        form['name'] = u'previous-button-works'

        response = submit_and_follow(app, form, env, 'save')
        form = response.forms['resource-edit']

        response = submit_and_follow(app, form, env, 'save', 'go-dataset')
        assert_true('dataset-edit' in response.forms)

    def test_previous_button_populates_form(self):
        app = self._get_test_app()
        env, response = _get_package_new_page(app)
        form = response.forms['dataset-edit']
        form['name'] = u'previous-button-populates-form'

        response = submit_and_follow(app, form, env, 'save')
        form = response.forms['resource-edit']

        response = submit_and_follow(app, form, env, 'save', 'go-dataset')
        form = response.forms['dataset-edit']
        assert_true('title' in form.fields)
        assert_equal(form['name'].value, u'previous-button-populates-form')

    def test_previous_next_maintains_draft_state(self):
        app = self._get_test_app()
        env, response = _get_package_new_page(app)
        form = response.forms['dataset-edit']
        form['name'] = u'previous-next-maintains-draft'

        response = submit_and_follow(app, form, env, 'save')
        form = response.forms['resource-edit']

        response = submit_and_follow(app, form, env, 'save', 'go-dataset')
        form = response.forms['dataset-edit']

        webtest_submit(form, 'save', status=302, extra_environ=env)
        pkg = model.Package.by_name(u'previous-next-maintains-draft')
        assert_equal(pkg.state, 'draft')

    def test_dataset_edit_org_dropdown_visible_to_normal_user_with_orgs_available(self):
        '''
        The 'Organization' dropdown is available on the dataset create/edit
        page to normal (non-sysadmin) users who have organizations available
        to them.
        '''
        user = factories.User()
        # user is admin of org.
        org = factories.Organization(name="my-org",
                                     users=[{'name': user['id'], 'capacity': 'admin'}])

        app = self._get_test_app()
        env = {'REMOTE_USER': user['name'].encode('ascii')}
        response = app.get(
            url=url_for(controller='package', action='new'),
            extra_environ=env,
        )

        # organization dropdown available in create page.
        form = response.forms['dataset-edit']
        assert 'owner_org' in form.fields

        # create dataset
        form['name'] = u'my-dataset'
        form['owner_org'] = org['id']
        response = submit_and_follow(app, form, env, 'save')

        # add a resource to make the pkg active
        resource_form = response.forms['resource-edit']
        resource_form['url'] = u'http://example.com/resource'
        submit_and_follow(app, resource_form, env, 'save', 'go-metadata')
        pkg = model.Package.by_name(u'my-dataset')
        assert_equal(pkg.state, 'active')

        # edit package page response
        url = url_for(controller='package',
                      action='edit',
                      id=pkg.id)
        pkg_edit_response = app.get(url=url, extra_environ=env)
        # A field with the correct id is in the response
        form = pkg_edit_response.forms['dataset-edit']
        assert 'owner_org' in form.fields
        # The organization id is in the response in a value attribute
        owner_org_options = [value for (value, _) in form['owner_org'].options]
        assert org['id'] in owner_org_options

    def test_dataset_edit_org_dropdown_normal_user_can_remove_org(self):
        '''
        A normal user (non-sysadmin) can remove an organization from a dataset
        have permissions on.
        '''
        user = factories.User()
        # user is admin of org.
        org = factories.Organization(name="my-org",
                                     users=[{'name': user['id'], 'capacity': 'admin'}])

        app = self._get_test_app()
        env = {'REMOTE_USER': user['name'].encode('ascii')}
        response = app.get(
            url=url_for(controller='package', action='new'),
            extra_environ=env,
        )

        # create dataset with owner_org
        form = response.forms['dataset-edit']
        form['name'] = u'my-dataset'
        form['owner_org'] = org['id']
        response = submit_and_follow(app, form, env, 'save')

        # add a resource to make the pkg active
        resource_form = response.forms['resource-edit']
        resource_form['url'] = u'http://example.com/resource'
        submit_and_follow(app, resource_form, env, 'save', 'go-metadata')
        pkg = model.Package.by_name(u'my-dataset')
        assert_equal(pkg.state, 'active')
        assert_equal(pkg.owner_org, org['id'])
        assert_not_equal(pkg.owner_org, None)

        # edit package page response
        url = url_for(controller='package',
                      action='edit',
                      id=pkg.id)
        pkg_edit_response = app.get(url=url, extra_environ=env)

        # edit dataset
        edit_form = pkg_edit_response.forms['dataset-edit']
        edit_form['owner_org'] = ''
        submit_and_follow(app, edit_form, env, 'save')
        post_edit_pkg = model.Package.by_name(u'my-dataset')
        assert_equal(post_edit_pkg.owner_org, None)
        assert_not_equal(post_edit_pkg.owner_org, org['id'])

    def test_dataset_edit_org_dropdown_not_visible_to_normal_user_with_no_orgs_available(self):
        '''
        The 'Organization' dropdown is not available on the dataset
        create/edit page to normal (non-sysadmin) users who have no
        organizations available to them.
        '''
        user = factories.User()
        # user isn't admin of org.
        org = factories.Organization(name="my-org")

        app = self._get_test_app()
        env = {'REMOTE_USER': user['name'].encode('ascii')}
        response = app.get(
            url=url_for(controller='package', action='new'),
            extra_environ=env,
        )

        # organization dropdown not in create page.
        form = response.forms['dataset-edit']
        assert 'owner_org' not in form.fields

        # create dataset
        form['name'] = u'my-dataset'
        response = submit_and_follow(app, form, env, 'save')

        # add a resource to make the pkg active
        resource_form = response.forms['resource-edit']
        resource_form['url'] = u'http://example.com/resource'
        submit_and_follow(app, resource_form, env, 'save', 'go-metadata')
        pkg = model.Package.by_name(u'my-dataset')
        assert_equal(pkg.state, 'active')

        # edit package response
        url = url_for(controller='package',
                      action='edit',
                      id=model.Package.by_name(u'my-dataset').id)
        pkg_edit_response = app.get(url=url, extra_environ=env)
        # A field with the correct id is in the response
        form = pkg_edit_response.forms['dataset-edit']
        assert 'owner_org' not in form.fields
        # The organization id is in the response in a value attribute
        assert 'value="{0}"'.format(org['id']) not in pkg_edit_response

    def test_dataset_edit_org_dropdown_visible_to_sysadmin_with_no_orgs_available(self):
        '''
        The 'Organization' dropdown is available to sysadmin users regardless
        of whether they personally have an organization they administrate.
        '''
        user = factories.User()
        sysadmin = factories.Sysadmin()
        # user is admin of org.
        org = factories.Organization(name="my-org",
                                     users=[{'name': user['id'], 'capacity': 'admin'}])

        app = self._get_test_app()
        # user in env is sysadmin
        env = {'REMOTE_USER': sysadmin['name'].encode('ascii')}
        response = app.get(
            url=url_for(controller='package', action='new'),
            extra_environ=env,
        )

        # organization dropdown available in create page.
        assert 'id="field-organizations"' in response

        # create dataset
        form = response.forms['dataset-edit']
        form['name'] = u'my-dataset'
        form['owner_org'] = org['id']
        response = submit_and_follow(app, form, env, 'save')

        # add a resource to make the pkg active
        resource_form = response.forms['resource-edit']
        resource_form['url'] = u'http://example.com/resource'
        submit_and_follow(app, resource_form, env, 'save', 'go-metadata')
        pkg = model.Package.by_name(u'my-dataset')
        assert_equal(pkg.state, 'active')

        # edit package page response
        url = url_for(controller='package',
                      action='edit',
                      id=pkg.id)
        pkg_edit_response = app.get(url=url, extra_environ=env)
        # A field with the correct id is in the response
        assert 'id="field-organizations"' in pkg_edit_response
        # The organization id is in the response in a value attribute
        assert 'value="{0}"'.format(org['id']) in pkg_edit_response


class TestPackageRead(helpers.FunctionalTestBase):
    @classmethod
    def setup_class(cls):
        super(cls, cls).setup_class()
        helpers.reset_db()

    def setup(self):
        model.repo.rebuild_db()

    def test_read(self):
        dataset = factories.Dataset()
        app = helpers._get_test_app()
        response = app.get(url_for(controller='package', action='read',
                                   id=dataset['name']))
        response.mustcontain('Test Dataset')
        response.mustcontain('Just another test dataset')

    def test_read_rdf(self):
        ''' The RDF outputs now live in ckanext-dcat'''
        dataset1 = factories.Dataset()

        offset = url_for(controller='package', action='read',
                         id=dataset1['name']) + ".rdf"
        app = self._get_test_app()
        app.get(offset, status=404)

    def test_read_n3(self):
        ''' The RDF outputs now live in ckanext-dcat'''
        dataset1 = factories.Dataset()

        offset = url_for(controller='package', action='read',
                         id=dataset1['name']) + ".n3"
        app = self._get_test_app()
        app.get(offset, status=404)


class TestPackageDelete(helpers.FunctionalTestBase):
    def test_owner_delete(self):
        user = factories.User()
        owner_org = factories.Organization(
            users=[{'name': user['id'], 'capacity': 'admin'}]
        )
        dataset = factories.Dataset(owner_org=owner_org['id'])

        app = helpers._get_test_app()
        env = {'REMOTE_USER': user['name'].encode('ascii')}
        response = app.post(
            url_for(controller='package', action='delete', id=dataset['name']),
            extra_environ=env,
        )
        response = response.follow()
        assert_equal(200, response.status_int)

        deleted = helpers.call_action('package_show', id=dataset['id'])
        assert_equal('deleted', deleted['state'])

    def test_delete_on_non_existing_dataset(self):
        app = helpers._get_test_app()
        response = app.post(
            url_for(controller='package', action='delete',
                    id='schrodingersdatset'),
            expect_errors=True,
        )
        assert_equal(404, response.status_int)

    def test_sysadmin_can_delete_any_dataset(self):
        owner_org = factories.Organization()
        dataset = factories.Dataset(owner_org=owner_org['id'])
        app = helpers._get_test_app()

        user = factories.Sysadmin()
        env = {'REMOTE_USER': user['name'].encode('ascii')}

        response = app.post(
            url_for(controller='package', action='delete', id=dataset['name']),
            extra_environ=env,
        )
        response = response.follow()
        assert_equal(200, response.status_int)

        deleted = helpers.call_action('package_show', id=dataset['id'])
        assert_equal('deleted', deleted['state'])

    def test_anon_user_cannot_delete_owned_dataset(self):
        user = factories.User()
        owner_org = factories.Organization(
            users=[{'name': user['id'], 'capacity': 'admin'}]
        )
        dataset = factories.Dataset(owner_org=owner_org['id'])

        app = helpers._get_test_app()
        response = app.post(
            url_for(controller='package', action='delete', id=dataset['name']),
        )
        response = response.follow()
        assert_equal(200, response.status_int)
        response.mustcontain('Unauthorized to delete package')

        deleted = helpers.call_action('package_show', id=dataset['id'])
        assert_equal('active', deleted['state'])

    def test_logged_in_user_cannot_delete_owned_dataset(self):
        owner = factories.User()
        owner_org = factories.Organization(
            users=[{'name': owner['id'], 'capacity': 'admin'}]
        )
        dataset = factories.Dataset(owner_org=owner_org['id'])

        app = helpers._get_test_app()
        user = factories.User()
        env = {'REMOTE_USER': user['name'].encode('ascii')}
        response = app.post(
            url_for(controller='package', action='delete', id=dataset['name']),
            extra_environ=env,
            expect_errors=True
        )
        assert_equal(401, response.status_int)
        response.mustcontain('Unauthorized to delete package')

    def test_confirm_cancel_delete(self):
        '''Test confirmation of deleting datasets

        When package_delete is made as a get request, it should return a
        'do you want to delete this dataset? confirmation page'''
        user = factories.User()
        owner_org = factories.Organization(
            users=[{'name': user['id'], 'capacity': 'admin'}]
        )
        dataset = factories.Dataset(owner_org=owner_org['id'])

        app = helpers._get_test_app()
        env = {'REMOTE_USER': user['name'].encode('ascii')}
        response = app.get(
            url_for(controller='package', action='delete', id=dataset['name']),
            extra_environ=env,
        )
        assert_equal(200, response.status_int)
        message = 'Are you sure you want to delete dataset - {name}?'
        response.mustcontain(message.format(name=dataset['name']))

        form = response.forms['confirm-dataset-delete-form']
        response = form.submit('cancel')
        response = helpers.webtest_maybe_follow(response)
        assert_equal(200, response.status_int)


class TestResourceRead(helpers.FunctionalTestBase):
    @classmethod
    def setup_class(cls):
        super(cls, cls).setup_class()

        if not p.plugin_loaded('image_view'):
            p.load('image_view')

        helpers.reset_db()

    @classmethod
    def teardown_class(cls):
        p.unload('image_view')

    def setup(self):
        model.repo.rebuild_db()

    def test_existent_resource_view_page_returns_ok_code(self):
        resource_view = factories.ResourceView()

        url = url_for(controller='package',
                      action='resource_read',
                      id=resource_view['package_id'],
                      resource_id=resource_view['resource_id'],
                      view_id=resource_view['id'])

        app = self._get_test_app()
        app.get(url, status=200)

    def test_inexistent_resource_view_page_returns_not_found_code(self):
        resource_view = factories.ResourceView()

        url = url_for(controller='package',
                      action='resource_read',
                      id=resource_view['package_id'],
                      resource_id=resource_view['resource_id'],
                      view_id='inexistent-view-id')

        app = self._get_test_app()
        app.get(url, status=404)

    def test_existing_resource_with_associated_dataset(self):

        dataset = factories.Dataset()
        resource = factories.Resource(package_id=dataset['id'])

        url = url_for(controller='package',
                      action='resource_read',
                      id=dataset['id'],
                      resource_id=resource['id'])

        app = self._get_test_app()
        app.get(url, status=200)

    def test_existing_resource_with_not_associated_dataset(self):

        dataset = factories.Dataset()
        resource = factories.Resource()

        url = url_for(controller='package',
                      action='resource_read',
                      id=dataset['id'],
                      resource_id=resource['id'])

        app = self._get_test_app()
        app.get(url, status=404)

    def test_resource_read_logged_in_user(self):
        '''
        A logged-in user can view resource page.
        '''
        user = factories.User()
        env = {'REMOTE_USER': user['name'].encode('ascii')}
        dataset = factories.Dataset()
        resource = factories.Resource(package_id=dataset['id'])

        url = url_for(controller='package',
                      action='resource_read',
                      id=dataset['id'],
                      resource_id=resource['id'])

        app = self._get_test_app()
        app.get(url, status=200, extra_environ=env)

    def test_resource_read_anon_user(self):
        '''
        An anon user can view resource page.
        '''
        dataset = factories.Dataset()
        resource = factories.Resource(package_id=dataset['id'])

        url = url_for(controller='package',
                      action='resource_read',
                      id=dataset['id'],
                      resource_id=resource['id'])

        app = self._get_test_app()
        app.get(url, status=200)

    def test_resource_read_sysadmin(self):
        '''
        A sysadmin can view resource page.
        '''
        sysadmin = factories.Sysadmin()
        env = {'REMOTE_USER': sysadmin['name'].encode('ascii')}
        dataset = factories.Dataset()
        resource = factories.Resource(package_id=dataset['id'])

        url = url_for(controller='package',
                      action='resource_read',
                      id=dataset['id'],
                      resource_id=resource['id'])

        app = self._get_test_app()
        app.get(url, status=200, extra_environ=env)


class TestResourceDelete(helpers.FunctionalTestBase):
    def test_dataset_owners_can_delete_resources(self):
        user = factories.User()
        owner_org = factories.Organization(
            users=[{'name': user['id'], 'capacity': 'admin'}]
        )
        dataset = factories.Dataset(owner_org=owner_org['id'])
        resource = factories.Resource(package_id=dataset['id'])
        app = helpers._get_test_app()
        env = {'REMOTE_USER': user['name'].encode('ascii')}
        response = app.post(
            url_for(controller='package', action='resource_delete',
                    id=dataset['name'], resource_id=resource['id']),
            extra_environ=env,
        )
        response = response.follow()
        assert_equal(200, response.status_int)
        response.mustcontain('This dataset has no data')

        assert_raises(p.toolkit.ObjectNotFound, helpers.call_action,
                      'resource_show', id=resource['id'])

    def test_deleting_non_existing_resource_404s(self):
        user = factories.User()
        owner_org = factories.Organization(
            users=[{'name': user['id'], 'capacity': 'admin'}]
        )
        dataset = factories.Dataset(owner_org=owner_org['id'])
        env = {'REMOTE_USER': user['name'].encode('ascii')}
        app = helpers._get_test_app()
        response = app.post(
            url_for(controller='package', action='resource_delete',
                    id=dataset['name'], resource_id='doesnotexist'),
            extra_environ=env,
            expect_errors=True
        )
        assert_equal(404, response.status_int)

    def test_anon_users_cannot_delete_owned_resources(self):
        user = factories.User()
        owner_org = factories.Organization(
            users=[{'name': user['id'], 'capacity': 'admin'}]
        )
        dataset = factories.Dataset(owner_org=owner_org['id'])
        resource = factories.Resource(package_id=dataset['id'])

        app = helpers._get_test_app()
        response = app.post(
            url_for(controller='package', action='resource_delete',
                    id=dataset['name'], resource_id=resource['id']),
        )
        response = response.follow()
        assert_equal(200, response.status_int)
        response.mustcontain('Unauthorized to delete package')

    def test_logged_in_users_cannot_delete_resources_they_do_not_own(self):
        # setup our dataset
        owner = factories.User()
        owner_org = factories.Organization(
            users=[{'name': owner['id'], 'capacity': 'admin'}]
        )
        dataset = factories.Dataset(owner_org=owner_org['id'])
        resource = factories.Resource(package_id=dataset['id'])

        # access as another user
        user = factories.User()
        env = {'REMOTE_USER': user['name'].encode('ascii')}
        app = helpers._get_test_app()
        response = app.post(
            url_for(controller='package', action='resource_delete',
                    id=dataset['name'], resource_id=resource['id']),
            extra_environ=env,
            expect_errors=True
        )
        assert_equal(401, response.status_int)
        response.mustcontain('Unauthorized to delete package')

    def test_sysadmins_can_delete_any_resource(self):
        owner_org = factories.Organization()
        dataset = factories.Dataset(owner_org=owner_org['id'])
        resource = factories.Resource(package_id=dataset['id'])

        sysadmin = factories.Sysadmin()
        app = helpers._get_test_app()
        env = {'REMOTE_USER': sysadmin['name'].encode('ascii')}
        response = app.post(
            url_for(controller='package', action='resource_delete',
                    id=dataset['name'], resource_id=resource['id']),
            extra_environ=env,
        )
        response = response.follow()
        assert_equal(200, response.status_int)
        response.mustcontain('This dataset has no data')

        assert_raises(p.toolkit.ObjectNotFound, helpers.call_action,
                      'resource_show', id=resource['id'])

    def test_confirm_and_cancel_deleting_a_resource(self):
        '''Test confirmation of deleting resources

        When resource_delete is made as a get request, it should return a
        'do you want to delete this reource? confirmation page'''
        user = factories.User()
        owner_org = factories.Organization(
            users=[{'name': user['id'], 'capacity': 'admin'}]
        )
        dataset = factories.Dataset(owner_org=owner_org['id'])
        resource = factories.Resource(package_id=dataset['id'])
        app = helpers._get_test_app()
        env = {'REMOTE_USER': user['name'].encode('ascii')}
        response = app.get(
            url_for(controller='package', action='resource_delete',
                    id=dataset['name'], resource_id=resource['id']),
            extra_environ=env,
        )
        assert_equal(200, response.status_int)
        message = 'Are you sure you want to delete resource - {name}?'
        response.mustcontain(message.format(name=resource['name']))

        # cancelling sends us back to the resource edit page
        form = response.forms['confirm-resource-delete-form']
        response = form.submit('cancel')
        response = response.follow()
        assert_equal(200, response.status_int)


class TestSearch(helpers.FunctionalTestBase):
    @classmethod
    def setup_class(cls):
        super(cls, cls).setup_class()
        helpers.reset_db()

    def test_search_basic(self):
        dataset1 = factories.Dataset()

        offset = url_for(controller='package', action='search')
        app = self._get_test_app()
        page = app.get(offset)

        assert dataset1['name'] in page.body.decode('utf8')

    def test_search_sort_by_blank(self):
        factories.Dataset()

        # ?sort has caused an exception in the past
        offset = url_for(controller='package', action='search') + '?sort'
        app = self._get_test_app()
        app.get(offset)

    def test_search_plugin_hooks(self):
        with p.use_plugin('test_package_controller_plugin') as plugin:

            offset = url_for(controller='package', action='search')
            app = self._get_test_app()
            app.get(offset)

            # get redirected ...
            assert plugin.calls['before_search'] == 1, plugin.calls
            assert plugin.calls['after_search'] == 1, plugin.calls

    def test_search_page_request(self):
        '''Requesting package search page returns list of datasets.'''
        app = self._get_test_app()
        factories.Dataset(name="dataset-one", title='Dataset One')
        factories.Dataset(name="dataset-two", title='Dataset Two')
        factories.Dataset(name="dataset-three", title='Dataset Three')

        search_url = url_for(controller='package', action='search')
        search_response = app.get(search_url)

        assert_true('3 datasets found' in search_response)

        search_response_html = BeautifulSoup(search_response.body)
        ds_titles = search_response_html.select('.dataset-list '
                                                '.dataset-item '
                                                '.dataset-heading a')
        ds_titles = [n.string for n in ds_titles]

        assert_equal(len(ds_titles), 3)
        assert_true('Dataset One' in ds_titles)
        assert_true('Dataset Two' in ds_titles)
        assert_true('Dataset Three' in ds_titles)

    def test_search_page_results(self):
        '''Searching for datasets returns expected results.'''
        app = self._get_test_app()
        factories.Dataset(name="dataset-one", title='Dataset One')
        factories.Dataset(name="dataset-two", title='Dataset Two')
        factories.Dataset(name="dataset-three", title='Dataset Three')

        search_url = url_for(controller='package', action='search')
        search_response = app.get(search_url)

        search_form = search_response.forms['dataset-search-form']
        search_form['q'] = 'One'
        search_results = webtest_submit(search_form)

        assert_true('1 dataset found' in search_results)

        search_response_html = BeautifulSoup(search_results.body)
        ds_titles = search_response_html.select('.dataset-list '
                                                '.dataset-item '
                                                '.dataset-heading a')
        ds_titles = [n.string for n in ds_titles]

        assert_equal(len(ds_titles), 1)
        assert_true('Dataset One' in ds_titles)

    def test_search_page_no_results(self):
        '''Search with non-returning phrase returns no results.'''
        app = self._get_test_app()
        factories.Dataset(name="dataset-one", title='Dataset One')
        factories.Dataset(name="dataset-two", title='Dataset Two')
        factories.Dataset(name="dataset-three", title='Dataset Three')

        search_url = url_for(controller='package', action='search')
        search_response = app.get(search_url)

        search_form = search_response.forms['dataset-search-form']
        search_form['q'] = 'Nout'
        search_results = webtest_submit(search_form)

        assert_true('No datasets found for &#34;Nout&#34;' in search_results)

        search_response_html = BeautifulSoup(search_results.body)
        ds_titles = search_response_html.select('.dataset-list '
                                                '.dataset-item '
                                                '.dataset-heading a')
        ds_titles = [n.string for n in ds_titles]

        assert_equal(len(ds_titles), 0)

    def test_search_page_results_tag(self):
        '''Searching with a tag returns expected results.'''
        app = self._get_test_app()
        factories.Dataset(name="dataset-one", title='Dataset One',
                          tags=[{'name': 'my-tag'}])
        factories.Dataset(name="dataset-two", title='Dataset Two')
        factories.Dataset(name="dataset-three", title='Dataset Three')

        search_url = url_for(controller='package', action='search')
        search_response = app.get(search_url)

        assert_true('/dataset?tags=my-tag' in search_response)

        tag_search_response = app.get('/dataset?tags=my-tag')

        assert_true('1 dataset found' in tag_search_response)

        search_response_html = BeautifulSoup(tag_search_response.body)
        ds_titles = search_response_html.select('.dataset-list '
                                                '.dataset-item '
                                                '.dataset-heading a')
        ds_titles = [n.string for n in ds_titles]

        assert_equal(len(ds_titles), 1)
        assert_true('Dataset One' in ds_titles)

    def test_search_page_results_private(self):
        '''Private datasets don't show up in dataset search results.'''
        app = self._get_test_app()
        org = factories.Organization()

        factories.Dataset(name="dataset-one", title='Dataset One',
                          owner_org=org['id'], private=True)
        factories.Dataset(name="dataset-two", title='Dataset Two')
        factories.Dataset(name="dataset-three", title='Dataset Three')

        search_url = url_for(controller='package', action='search')
        search_response = app.get(search_url)

        search_response_html = BeautifulSoup(search_response.body)
        ds_titles = search_response_html.select('.dataset-list '
                                                '.dataset-item '
                                                '.dataset-heading a')
        ds_titles = [n.string for n in ds_titles]

        assert_equal(len(ds_titles), 2)
        assert_true('Dataset One' not in ds_titles)
        assert_true('Dataset Two' in ds_titles)
        assert_true('Dataset Three' in ds_titles)


class TestPackageFollow(helpers.FunctionalTestBase):

    def test_package_follow(self):
        app = self._get_test_app()

        user = factories.User()
        package = factories.Dataset()

        env = {'REMOTE_USER': user['name'].encode('ascii')}
        follow_url = url_for(controller='package',
                             action='follow',
                             id=package['id'])
        response = app.post(follow_url, extra_environ=env, status=302)
        response = response.follow()
        assert_true('You are now following {0}'
                    .format(package['title'])
                    in response)

    def test_package_follow_not_exist(self):
        '''Pass an id for a package that doesn't exist'''
        app = self._get_test_app()

        user_one = factories.User()

        env = {'REMOTE_USER': user_one['name'].encode('ascii')}
        follow_url = url_for(controller='package',
                             action='follow',
                             id='not-here')
        response = app.post(follow_url, extra_environ=env, status=302)
        response = response.follow(status=404)
        assert_true('Dataset not found' in response)

    def test_package_unfollow(self):
        app = self._get_test_app()

        user_one = factories.User()
        package = factories.Dataset()

        env = {'REMOTE_USER': user_one['name'].encode('ascii')}
        follow_url = url_for(controller='package',
                             action='follow',
                             id=package['id'])
        app.post(follow_url, extra_environ=env, status=302)

        unfollow_url = url_for(controller='package', action='unfollow',
                               id=package['id'])
        unfollow_response = app.post(unfollow_url, extra_environ=env,
                                     status=302)
        unfollow_response = unfollow_response.follow()

        assert_true('You are no longer following {0}'
                    .format(package['title'])
                    in unfollow_response)

    def test_package_unfollow_not_following(self):
        '''Unfollow a package not currently following'''
        app = self._get_test_app()

        user_one = factories.User()
        package = factories.Dataset()

        env = {'REMOTE_USER': user_one['name'].encode('ascii')}
        unfollow_url = url_for(controller='package', action='unfollow',
                               id=package['id'])
        unfollow_response = app.post(unfollow_url, extra_environ=env,
                                     status=302)
        unfollow_response = unfollow_response.follow()

        assert_true('You are not following {0}'.format(package['id'])
                    in unfollow_response)

    def test_package_unfollow_not_exist(self):
        '''Unfollow a package that doesn't exist.'''
        app = self._get_test_app()

        user_one = factories.User()

        env = {'REMOTE_USER': user_one['name'].encode('ascii')}
        unfollow_url = url_for(controller='package', action='unfollow',
                               id='not-here')
        unfollow_response = app.post(unfollow_url, extra_environ=env,
                                     status=302)
        unfollow_response = unfollow_response.follow(status=404)
        assert_true('Dataset not found' in unfollow_response)

    def test_package_follower_list(self):
        '''Following users appear on followers list page.'''
        app = self._get_test_app()

        user_one = factories.Sysadmin()
        package = factories.Dataset()

        env = {'REMOTE_USER': user_one['name'].encode('ascii')}
        follow_url = url_for(controller='package',
                             action='follow',
                             id=package['id'])
        app.post(follow_url, extra_environ=env, status=302)

        followers_url = url_for(controller='package', action='followers',
                                id=package['id'])

        # Only sysadmins can view the followers list pages
        followers_response = app.get(followers_url, extra_environ=env,
                                     status=200)
        assert_true(user_one['display_name'] in followers_response)
