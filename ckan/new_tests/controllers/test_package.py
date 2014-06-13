from nose.tools import assert_equal, assert_true

from routes import url_for

import ckan.new_tests.helpers as helpers
import ckan.new_tests.factories as factories
import ckan.model as model

webtest_submit = helpers.webtest_submit


class TestPackageControllerNew(helpers.FunctionalTestBase):
    def _get_package_new_page_as_sysadmin(self):
        user = factories.Sysadmin()
        env = {'REMOTE_USER': user['name'].encode('ascii')}
        response = self.app.get(
            url=url_for(controller='package', action='new'),
            extra_environ=env,
        )
        return env, response

    def test_form_renders(self):
        env, response = self._get_package_new_page_as_sysadmin()
        assert_true('dataset-edit' in response.forms)

    def test_name_required(self):
        env, response = self._get_package_new_page_as_sysadmin()
        form = response.forms['dataset-edit']

        response = webtest_submit(form, 'save', status=200, extra_environ=env)
        assert_true('dataset-edit' in response.forms)
        assert_true('Name: Missing value' in response)

    def test_resource_form_renders(self):
        env, response = self._get_package_new_page_as_sysadmin()
        form = response.forms['dataset-edit']
        form['name'] = u'resource-form-renders'

        response = self._submit_and_follow(form, env, 'save')
        assert_true('resource-edit' in response.forms)

    def test_first_page_creates_draft_package(self):
        env, response = self._get_package_new_page_as_sysadmin()
        form = response.forms['dataset-edit']
        form['name'] = u'first-page-creates-draft'

        webtest_submit(form, 'save', status=302, extra_environ=env)
        pkg = model.Package.by_name(u'first-page-creates-draft')
        assert_equal(pkg.state, 'draft')

    def test_previous_button_works(self):
        env, response = self._get_package_new_page_as_sysadmin()
        form = response.forms['dataset-edit']
        form['name'] = u'previous-button-works'

        response = self._submit_and_follow(form, env, 'save')
        form = response.forms['resource-edit']

        response = self._submit_and_follow(form, env, 'save', 'go-dataset')
        assert_true('dataset-edit' in response.forms)

    def test_previous_button_populates_form(self):
        env, response = self._get_package_new_page_as_sysadmin()
        form = response.forms['dataset-edit']
        form['name'] = u'previous-button-populates-form'

        response = self._submit_and_follow(form, env, 'save')
        form = response.forms['resource-edit']

        response = self._submit_and_follow(form, env, 'save', 'go-dataset')
        form = response.forms['dataset-edit']
        assert_true('title' in form.fields)
        assert_equal(form['name'].value, u'previous-button-populates-form')

    def test_previous_next_maintains_draft_state(self):
        env, response = self._get_package_new_page_as_sysadmin()
        form = response.forms['dataset-edit']
        form['name'] = u'previous-next-maintains-draft'

        response = self._submit_and_follow(form, env, 'save')
        form = response.forms['resource-edit']

        response = self._submit_and_follow(form, env, 'save', 'go-dataset')
        form = response.forms['dataset-edit']

        webtest_submit(form, 'save', status=302, extra_environ=env)
        pkg = model.Package.by_name(u'previous-next-maintains-draft')
        assert_equal(pkg.state, 'draft')
