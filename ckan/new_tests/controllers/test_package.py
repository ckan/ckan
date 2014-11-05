from nose.tools import assert_equal, assert_true

from routes import url_for

import ckan.model as model
import ckan.plugins as p

import ckan.new_tests.helpers as helpers
import ckan.new_tests.factories as factories


webtest_submit = helpers.webtest_submit
submit_and_follow = helpers.submit_and_follow


def _get_package_new_page_as_sysadmin(app):
    user = factories.Sysadmin()
    env = {'REMOTE_USER': user['name'].encode('ascii')}
    response = app.get(
        url=url_for(controller='package', action='new'),
        extra_environ=env,
    )
    return env, response


class TestPackageControllerNew(helpers.FunctionalTestBase):
    def test_form_renders(self):
        app = self._get_test_app()
        env, response = _get_package_new_page_as_sysadmin(app)
        assert_true('dataset-edit' in response.forms)

    def test_name_required(self):
        app = self._get_test_app()
        env, response = _get_package_new_page_as_sysadmin(app)
        form = response.forms['dataset-edit']

        response = webtest_submit(form, 'save', status=200, extra_environ=env)
        assert_true('dataset-edit' in response.forms)
        assert_true('Name: Missing value' in response)

    def test_resource_form_renders(self):
        app = self._get_test_app()
        env, response = _get_package_new_page_as_sysadmin(app)
        form = response.forms['dataset-edit']
        form['name'] = u'resource-form-renders'

        response = submit_and_follow(app, form, env, 'save')
        assert_true('resource-edit' in response.forms)

    def test_first_page_creates_draft_package(self):
        app = self._get_test_app()
        env, response = _get_package_new_page_as_sysadmin(app)
        form = response.forms['dataset-edit']
        form['name'] = u'first-page-creates-draft'

        webtest_submit(form, 'save', status=302, extra_environ=env)
        pkg = model.Package.by_name(u'first-page-creates-draft')
        assert_equal(pkg.state, 'draft')

    def test_resource_required(self):
        app = self._get_test_app()
        env, response = _get_package_new_page_as_sysadmin(app)
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
        env, response = _get_package_new_page_as_sysadmin(app)
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
        env, response = _get_package_new_page_as_sysadmin(app)
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
        env, response = _get_package_new_page_as_sysadmin(app)
        form = response.forms['dataset-edit']
        form['name'] = u'previous-button-works'

        response = submit_and_follow(app, form, env, 'save')
        form = response.forms['resource-edit']

        response = submit_and_follow(app, form, env, 'save', 'go-dataset')
        assert_true('dataset-edit' in response.forms)

    def test_previous_button_populates_form(self):
        app = self._get_test_app()
        env, response = _get_package_new_page_as_sysadmin(app)
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
        env, response = _get_package_new_page_as_sysadmin(app)
        form = response.forms['dataset-edit']
        form['name'] = u'previous-next-maintains-draft'

        response = submit_and_follow(app, form, env, 'save')
        form = response.forms['resource-edit']

        response = submit_and_follow(app, form, env, 'save', 'go-dataset')
        form = response.forms['dataset-edit']

        webtest_submit(form, 'save', status=302, extra_environ=env)
        pkg = model.Package.by_name(u'previous-next-maintains-draft')
        assert_equal(pkg.state, 'draft')


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
