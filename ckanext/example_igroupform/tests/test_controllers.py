# encoding: utf-8

from nose.tools import assert_equal, assert_in
from ckan.lib.helpers import url_for

import ckan.plugins as plugins
import ckan.tests.helpers as helpers
import ckan.model as model
from ckan.tests import factories

webtest_submit = helpers.webtest_submit
submit_and_follow = helpers.submit_and_follow

custom_group_type = u'grup'
group_type = u'group'


def _get_group_new_page(app, group_type):
    user = factories.User()
    env = {'REMOTE_USER': user['name'].encode('ascii')}
    response = app.get(
        url_for('%s_new' % group_type),
        extra_environ=env,
    )
    return env, response


class TestGroupController(helpers.FunctionalTestBase):
    @classmethod
    def setup_class(cls):
        super(TestGroupController, cls).setup_class()
        plugins.load('example_igroupform')

    @classmethod
    def teardown_class(cls):
        plugins.unload('example_igroupform')
        super(TestGroupController, cls).teardown_class()

    def test_about(self):
        app = self._get_test_app()
        user = factories.User()
        group = factories.Group(user=user, type=custom_group_type)
        group_name = group['name']
        env = {'REMOTE_USER': user['name'].encode('ascii')}
        url = url_for('%s_about' % custom_group_type,
                      id=group_name)
        response = app.get(url=url, extra_environ=env)
        response.mustcontain(group_name)

    def test_bulk_process(self):
        app = self._get_test_app()
        user = factories.User()
        group = factories.Group(user=user, type=custom_group_type)
        group_name = group['name']
        env = {'REMOTE_USER': user['name'].encode('ascii')}
        url = url_for('%s_bulk_process' % custom_group_type,
                      id=group_name)
        try:
            response = app.get(url=url, extra_environ=env)
        except Exception as e:
            assert (e.args == ('Must be an organization', ))
        else:
            raise Exception("Response should have raised an exception")

    def test_delete(self):
        app = self._get_test_app()
        user = factories.User()
        group = factories.Group(user=user, type=custom_group_type)
        group_name = group['name']
        env = {'REMOTE_USER': user['name'].encode('ascii')}
        url = url_for('%s_action' % custom_group_type, action='delete',
                      id=group_name)
        response = app.get(url=url, extra_environ=env)

    def test_custom_group_form_slug(self):
        app = self._get_test_app()
        env, response = _get_group_new_page(app, custom_group_type)

        assert '<span class="input-group-addon">/{}/</span>'.format(
            custom_group_type) in response
        assert 'placeholder="my-{}"'.format(
            custom_group_type) in response
        assert 'data-module-prefix="test.ckan.net/{}/"'.format(
            custom_group_type) in response
        assert 'data-module-placeholder="&lt;{}&gt;"'.format(
            custom_group_type) in response


class TestOrganizationController(helpers.FunctionalTestBase):
    @classmethod
    def setup_class(cls):
        super(TestOrganizationController, cls).setup_class()
        plugins.load('example_igroupform_organization')

    @classmethod
    def teardown_class(cls):
        plugins.unload('example_igroupform_organization')
        super(TestOrganizationController, cls).teardown_class()

    def test_about(self):
        app = self._get_test_app()
        user = factories.User()
        group = factories.Organization(user=user, type=custom_group_type)
        group_name = group['name']
        env = {'REMOTE_USER': user['name'].encode('ascii')}
        url = url_for('%s_about' % custom_group_type,
                      id=group_name)
        response = app.get(url=url, extra_environ=env)
        response.mustcontain(group_name)

    def test_bulk_process(self):
        app = self._get_test_app()
        user = factories.User()
        group = factories.Organization(user=user, type=custom_group_type)
        group_name = group['name']
        env = {'REMOTE_USER': user['name'].encode('ascii')}
        url = url_for('%s_bulk_process' % custom_group_type,
                      id=group_name)
        response = app.get(url=url, extra_environ=env)

    def test_delete(self):
        app = self._get_test_app()
        user = factories.User()
        group = factories.Organization(user=user, type=custom_group_type)
        group_name = group['name']
        env = {'REMOTE_USER': user['name'].encode('ascii')}
        url = url_for('%s_action' % custom_group_type, action='delete',
                      id=group_name)
        response = app.get(url=url, extra_environ=env)

    def test_custom_org_form_slug(self):
        app = self._get_test_app()
        env, response = _get_group_new_page(app, custom_group_type)

        assert '<span class="input-group-addon">/{}/</span>'.format(
            custom_group_type) in response
        assert 'placeholder="my-{}"'.format(
            custom_group_type) in response
        assert 'data-module-prefix="test.ckan.net/{}/"'.format(
            custom_group_type) in response
        assert 'data-module-placeholder="&lt;{}&gt;"'.format(
            custom_group_type) in response


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
        env, response = _get_group_new_page(app, custom_group_type)
        form = response.forms['group-edit']
        form['name'] = u'saved'

        response = submit_and_follow(app, form, env, 'save')
        # check correct redirect
        assert_equal(response.req.url,
                     'http://test.ckan.net/%s/saved' % custom_group_type)
        # check saved ok
        group = model.Group.by_name(u'saved')
        assert_equal(group.title, u'')
        assert_equal(group.type, custom_group_type)
        assert_equal(group.state, 'active')

    def test_custom_group_form(self):
        '''Our custom group form is being used for new groups.'''
        app = self._get_test_app()
        env, response = _get_group_new_page(app, custom_group_type)

        assert_in('My Custom Group Form!', response,
                  msg="Custom group form not being used.")


class TestGroupControllerNew_DefaultGroupType(helpers.FunctionalTestBase):
    @classmethod
    def setup_class(cls):
        super(TestGroupControllerNew_DefaultGroupType, cls).setup_class()
        plugins.load('example_igroupform_default_group_type')

    @classmethod
    def teardown_class(cls):
        plugins.unload('example_igroupform_default_group_type')
        super(TestGroupControllerNew_DefaultGroupType, cls).teardown_class()

    def test_save(self):
        app = self._get_test_app()
        env, response = _get_group_new_page(app, group_type)
        form = response.forms['group-edit']
        form['name'] = u'saved'

        response = submit_and_follow(app, form, env, 'save')
        # check correct redirect
        assert_equal(response.req.url,
                     'http://test.ckan.net/%s/saved' % group_type)
        # check saved ok
        group = model.Group.by_name(u'saved')
        assert_equal(group.title, u'')
        assert_equal(group.type, group_type)
        assert_equal(group.state, 'active')

    def test_custom_group_form(self):
        '''Our custom group form is being used for new groups.'''
        app = self._get_test_app()
        env, response = _get_group_new_page(app, group_type)

        assert_in('My Custom Group Form!', response,
                  msg="Custom group form not being used.")


def _get_group_edit_page(app, group_type, group_name=None):
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
        url = url_for('%s_edit' % custom_group_type,
                      id='doesnt_exist')
        app.get(url=url, extra_environ=env,
                status=404)

    def test_save(self):
        app = self._get_test_app()
        env, response, group_name = \
            _get_group_edit_page(app, custom_group_type)
        form = response.forms['group-edit']

        response = submit_and_follow(app, form, env, 'save')
        group = model.Group.by_name(group_name)
        assert_equal(group.state, 'active')
        assert_equal(group.type, custom_group_type)

    def test_custom_group_form(self):
        '''Our custom group form is being used to edit groups.'''
        app = self._get_test_app()
        env, response, group_name = \
            _get_group_edit_page(app, custom_group_type)

        assert_in('My Custom Group Form!', response,
                  msg="Custom group form not being used.")


class TestGroupControllerEdit_DefaultGroupType(helpers.FunctionalTestBase):
    @classmethod
    def setup_class(cls):
        super(TestGroupControllerEdit_DefaultGroupType, cls).setup_class()
        plugins.load('example_igroupform_default_group_type')

    @classmethod
    def teardown_class(cls):
        plugins.unload('example_igroupform_default_group_type')
        super(TestGroupControllerEdit_DefaultGroupType, cls).teardown_class()

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
        env, response, group_name = _get_group_edit_page(app, group_type)
        form = response.forms['group-edit']

        response = submit_and_follow(app, form, env, 'save')
        group = model.Group.by_name(group_name)
        assert_equal(group.state, 'active')
        assert_equal(group.type, group_type)

    def test_custom_group_form(self):
        '''Our custom group form is being used to edit groups.'''
        app = self._get_test_app()
        env, response, group_name = _get_group_edit_page(app, group_type)

        assert_in('My Custom Group Form!', response,
                  msg="Custom group form not being used.")
