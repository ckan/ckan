# encoding: utf-8

from nose.tools import assert_equal
from ckan.lib.helpers import url_for

import ckan.plugins as plugins
import ckan.tests.helpers as helpers
import ckan.tests.factories as factories
import ckan.model as model

submit_and_follow = helpers.submit_and_follow


def _get_package_edit_page(app, package_name):
    user = factories.User()
    env = {'REMOTE_USER': user['name'].encode('ascii')}
    response = app.get(
        url=url_for(controller='package', action='edit', id=package_name),
        extra_environ=env,
    )
    return env, response


class TestPackageController(helpers.FunctionalTestBase):
    @classmethod
    def setup_class(cls):
        super(TestPackageController, cls).setup_class()
        plugins.load('example_idatasetform')

    @classmethod
    def teardown_class(cls):
        plugins.unload('example_idatasetform')
        super(TestPackageController, cls).teardown_class()

    def test_edit_converted_extra_field(self):
        dataset = factories.Dataset(custom_text='foo')
        app = self._get_test_app()
        env, response = _get_package_edit_page(app, dataset['name'])
        form = response.forms['dataset-edit']
        form['custom_text'] = u'bar'

        response = submit_and_follow(app, form, env, 'save')
        # just check it has finished the edit, rather than being sent on to the
        # resource create/edit form.
        assert_equal(response.req.path, '/dataset/%s' % dataset['name'])

        pkg = model.Package.by_name(dataset['name'])
        assert_equal(pkg.extras['custom_text'], u'bar')

    def test_edit_custom_extra_field(self):
        # i.e. an extra field that is not mentioned in the schema, filled in on
        # the form in the 'custom-fields' section
        dataset = factories.Dataset(extras=[{'key': 'testkey',
                                             'value': 'foo'}])
        app = self._get_test_app()
        env, response = _get_package_edit_page(app, dataset['name'])
        form = response.forms['dataset-edit']
        form['extras__0__value'] = u'bar'

        response = submit_and_follow(app, form, env, 'save')
        # just check it has finished the edit, rather than being sent on to the
        # resource create/edit form.
        assert_equal(response.req.path, '/dataset/%s' % dataset['name'])

        pkg = model.Package.by_name(dataset['name'])
        assert_equal(pkg.extras['testkey'], u'bar')
