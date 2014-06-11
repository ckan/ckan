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

    def test_next_button_works(self):
        user = factories.Sysadmin()
        env = {'REMOTE_USER': user['name'].encode('ascii')}
        response = self.app.get(
            url=url_for(controller='package', action='new'),
            extra_environ=env,
        )
        form = response.forms['dataset-edit']
        form['name'] = u'next-button-works'
        form['title'] = u'Next button works'

        response = webtest_submit(form, 'save', status=302, extra_environ=env)
        assert_true('Location' in dict(response.headers))

    def test_resource_form_renders(self):
        user = factories.Sysadmin()
        env = {'REMOTE_USER': user['name'].encode('ascii')}
        response = self.app.get(
            url=url_for(controller='package', action='new'),
            extra_environ=env,
        )
        form = response.forms['dataset-edit']
        form['name'] = u'resource-form-renders'
        form['title'] = u'Resource form renders'

        response = webtest_submit(form, 'save', status=302, extra_environ=env)
        response = self.app.get(
            url=dict(response.headers)['Location'],
            extra_environ=env,
        )
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
        form['title'] = u'Previous button works'

        response = webtest_submit(form, 'save', status=302, extra_environ=env)
        response = self.app.get(
            url=dict(response.headers)['Location'],
            extra_environ=env,
        )
        form = response.forms['resource-edit']
        response = webtest_submit(form, 'save', value='go-dataset',
                                  status=302, extra_environ=env)
        response = self.app.get(
            url=dict(response.headers)['Location'],
            extra_environ=env,
        )
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
        form['title'] = u'Previous button populates form'

        response = webtest_submit(form, 'save', status=302, extra_environ=env)
        response = self.app.get(
            url=dict(response.headers)['Location'],
            extra_environ=env,
        )
        form = response.forms['resource-edit']
        response = webtest_submit(form, 'save', value='go-dataset',
                                  status=302, extra_environ=env)
        response = self.app.get(
            url=dict(response.headers)['Location'],
            extra_environ=env,
        )
        form = response.forms['dataset-edit']
        assert_true('title' in form.fields)
        assert_equal(form['title'].value, u'Previous button populates form')
        assert_equal(form['name'].value, u'previous-button-populates-form')
