from nose.tools import assert_equal
from routes import url_for

import ckan.plugins as plugins
import ckan.new_tests.helpers as helpers
import ckan.model as model
from ckan.new_tests import factories

assert_in = helpers.assert_in
webtest_submit = helpers.webtest_submit
submit_and_follow = helpers.submit_and_follow

group_type = u'grup'


def _get_group_new_page(app):
    user = factories.User()
    env = {'REMOTE_USER': user['name'].encode('ascii')}
    response = app.get(
        url_for('%s_new' % group_type),
        extra_environ=env,
    )
    return env, response


class TestGroupControllerNew(helpers.FunctionalTestBase):
    @classmethod
    def setup_class(cls):
        super(TestGroupControllerNew, cls).setup_class()
        plugins.load('example_igroupform')

    @classmethod
    def teardown_class(cls):
        plugins.unload('example_igroupform')
        super(TestGroupControllerNew, cls).teardown_class()

    def test_save(self):
        app = self._get_test_app()
        env, response = _get_group_new_page(app)
        form = response.forms['group-edit']
        form['name'] = u'saved'

        response = submit_and_follow(app, form, env, 'save')
        # check correct redirect
        assert_equal(response.req.url,
                     'http://localhost/%s/saved' % group_type)
        # check saved ok
        group = model.Group.by_name(u'saved')
        assert_equal(group.title, u'')
        assert_equal(group.type, group_type)
        assert_equal(group.state, 'active')


def _get_group_edit_page(app, group_name=None):
    user = factories.User()
    if group_name is None:
        group = factories.Group(user=user, type=group_type)
        group_name = group['name']
    env = {'REMOTE_USER': user['name'].encode('ascii')}
    url = url_for('%s_edit' % group_type,
                  id=group_name)
    response = app.get(url=url, extra_environ=env)
    return env, response, group_name


class TestGroupControllerEdit(helpers.FunctionalTestBase):
    @classmethod
    def setup_class(cls):
        super(TestGroupControllerEdit, cls).setup_class()
        plugins.load('example_igroupform')

    @classmethod
    def teardown_class(cls):
        plugins.unload('example_igroupform')
        super(TestGroupControllerEdit, cls).teardown_class()

    def test_group_doesnt_exist(self):
        app = self._get_test_app()
        user = factories.User()
        env = {'REMOTE_USER': user['name'].encode('ascii')}
        url = url_for('%s_edit' % group_type,
                      id='doesnt_exist')
        app.get(url=url, extra_environ=env,
                status=404)

    def test_save(self):
        app = self._get_test_app()
        env, response, group_name = _get_group_edit_page(app)
        form = response.forms['group-edit']

        response = submit_and_follow(app, form, env, 'save')
        group = model.Group.by_name(group_name)
        assert_equal(group.state, 'active')
        assert_equal(group.type, group_type)
