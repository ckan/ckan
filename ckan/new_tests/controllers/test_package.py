from nose.tools import assert_equal, assert_true

from routes import url_for

import ckan.new_tests.helpers as helpers
import ckan.new_tests.factories as factories


class TestPackageController(helpers.FunctionalTestBaseClass):
    def test_create_form_renders(self):
        user = factories.Sysadmin()
        extra_environ = {
            'REMOTE_USER': user['name'].encode('ascii'),
        }
        response = self.app.get(
            url=url_for(controller='package', action='new'),
            extra_environ=extra_environ,
        )
        assert_true('dataset-edit' in response.forms)

    def test_create_form_next_button_works(self):
        user = factories.Sysadmin()
        extra_environ = {
            'REMOTE_USER': user['name'].encode('ascii'),
        }
        response = self.app.get(
            url=url_for(controller='package', action='new'),
            extra_environ=extra_environ,
        )
        form = response.forms['dataset-edit']
        form['name'] = u'next-button-works'
        form['title'] = u'Next button works'

        response = form.submit(
            'save',
            status=302,
            extra_environ=extra_environ,
        )
        assert_true('Location' in dict(response.headers))

    def test_create_form_resource_form_renders(self):
        user = factories.Sysadmin()
        extra_environ = {
            'REMOTE_USER': user['name'].encode('ascii'),
        }
        response = self.app.get(
            url=url_for(controller='package', action='new'),
            extra_environ=extra_environ,
        )
        form = response.forms['dataset-edit']
        form['name'] = u'resource-form-renders'
        form['title'] = u'Resource form renders'

        response = form.submit(
            'save',
            status=302,
            extra_environ=extra_environ,
        )
        response = self.app.get(
            url=dict(response.headers)['Location'],
            extra_environ=extra_environ,
        )
        assert_true('resource-edit' in response.forms)
