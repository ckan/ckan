from nose.tools import assert_equal, assert_true

from routes import url_for

import ckan.model as model

import ckan.new_tests.helpers as helpers
import ckan.new_tests.factories as factories


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

    def test_complete_package_with_one_resource(self):
        app = self._get_test_app()
        env, response = _get_package_new_page(app)
        form = response.forms[1]
        form['name'] = u'complete-package-with-one-resource'

        response = submit_and_follow(app, form, env, 'save')
        form = response.forms[1]
        form['url'] = u'http://example.com/resource'

        response = submit_and_follow(app, form, env, 'save', 'go-metadata')

        form = response.forms[1]
        form['version'] = '2.0'
        response = submit_and_follow(app, form, env, 'save', 'finish')

        pkg = model.Package.by_name(u'complete-package-with-one-resource')
        assert_equal(pkg.resources[0].url, u'http://example.com/resource')
        assert_equal(pkg.version, '2.0')
        assert_equal(pkg.state, 'active')
