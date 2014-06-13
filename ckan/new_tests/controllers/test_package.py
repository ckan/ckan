from nose.tools import assert_equal, assert_true

from routes import url_for

import ckan.new_tests.helpers as helpers
import ckan.new_tests.factories as factories

webtest_submit = helpers.webtest_submit


class TestPackageControllerNew(helpers.FunctionalTestBase):
    def test_form_renders(self):
        user = factories.Sysadmin()
        env = {'REMOTE_USER': user['name'].encode('ascii')}
        response = self.app.get(
            url=url_for(controller='package', action='new'),
            extra_environ=env,
        )
        assert_true('dataset-edit' in response.forms)

    def test_name_required(self):
        user = factories.Sysadmin()
        env = {'REMOTE_USER': user['name'].encode('ascii')}
        response = self.app.get(
            url=url_for(controller='package', action='new'),
            extra_environ=env,
        )
        form = response.forms['dataset-edit']

        response = webtest_submit(form, 'save', status=200, extra_environ=env)
        assert_true('dataset-edit' in response.forms)
        assert_true('Name: Missing value' in response)

    def test_resource_form_renders(self):
        user = factories.Sysadmin()
        env = {'REMOTE_USER': user['name'].encode('ascii')}
        response = self.app.get(
            url=url_for(controller='package', action='new'),
            extra_environ=env,
        )
        form = response.forms['dataset-edit']
        form['name'] = u'resource-form-renders'

        response = self._submit_and_follow(form, env, 'save')
        assert_true('resource-edit' in response.forms)

    def test_previous_button_works(self):
        user = factories.Sysadmin()
        env = {'REMOTE_USER': user['name'].encode('ascii')}
        response = self.app.get(
            url=url_for(controller='package', action='new'),
            extra_environ=env,
        )
        form = response.forms['dataset-edit']
        form['name'] = u'previous-button-works'

        response = self._submit_and_follow(form, env, 'save')
        form = response.forms['resource-edit']

        response = self._submit_and_follow(form, env, 'save', 'go-dataset')
        assert_true('dataset-edit' in response.forms)

    def test_previous_button_populates_form(self):
        user = factories.Sysadmin()
        env = {'REMOTE_USER': user['name'].encode('ascii')}
        response = self.app.get(
            url=url_for(controller='package', action='new'),
            extra_environ=env,
        )
        form = response.forms['dataset-edit']
        form['name'] = u'previous-button-populates-form'

        response = self._submit_and_follow(form, env, 'save')
        form = response.forms['resource-edit']

        response = self._submit_and_follow(form, env, 'save', 'go-dataset')
        form = response.forms['dataset-edit']
        assert_true('title' in form.fields)
        # name gets copied to title by default validators
        assert_equal(form['title'].value, u'previous-button-populates-form')
        assert_equal(form['name'].value, u'previous-button-populates-form')
