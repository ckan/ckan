from nose.tools import assert_equal, assert_true, assert_not_equal

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


class TestPackageResourceRead(helpers.FunctionalTestBase):
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


class TestPackageRead(helpers.FunctionalTestBase):
    @classmethod
    def setup_class(cls):
        super(cls, cls).setup_class()
        helpers.reset_db()

    def setup(self):
        model.repo.rebuild_db()

    def test_read_rdf(self):
        dataset1 = factories.Dataset()

        offset = url_for(controller='package', action='read',
                         id=dataset1['name']) + ".rdf"
        app = self._get_test_app()
        res = app.get(offset, status=200)

        assert 'dcat' in res, res
        assert '{{' not in res, res

    def test_read_n3(self):
        dataset1 = factories.Dataset()

        offset = url_for(controller='package', action='read',
                         id=dataset1['name']) + ".n3"
        app = self._get_test_app()
        res = app.get(offset, status=200)

        assert 'dcat' in res, res
        assert '{{' not in res, res


class TestSearch(helpers.FunctionalTestBase):
    @classmethod
    def setup_class(cls):
        super(cls, cls).setup_class()
        helpers.reset_db()

    def setup(self):
        model.repo.rebuild_db()

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
