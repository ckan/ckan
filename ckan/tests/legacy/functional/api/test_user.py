# encoding: utf-8

from nose.tools import assert_equal

import ckan.logic as logic
from ckan import model
from ckan.lib.create_test_data import CreateTestData
from ckan.tests.legacy import TestController as ControllerTestCase
from ckan.tests.legacy import url_for
from ckan.tests import helpers

from ckan.common import json


class TestUserApi(ControllerTestCase):
    @classmethod
    def setup_class(cls):
        CreateTestData.create()

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()

    def test_autocomplete(self):
        response = self.app.get(
            url=url_for(controller='api', action='user_autocomplete', ver=2),
            params={
               'q': u'sysadmin',
            },
            status=200,
        )
        print(response.json)
        assert set(response.json[0].keys()) == set(['id', 'name', 'fullname'])
        assert_equal(response.json[0]['name'], u'testsysadmin')
        assert_equal(response.headers.get('Content-Type'), 'application/json;charset=utf-8')

    def test_autocomplete_multiple(self):
        response = self.app.get(
            url=url_for(controller='api', action='user_autocomplete', ver=2),
            params={
               'q': u'tes',
            },
            status=200,
        )
        print(response.json)
        assert_equal(len(response.json), 2)

    def test_autocomplete_limit(self):
        response = self.app.get(
            url=url_for(controller='api', action='user_autocomplete', ver=2),
            params={
               'q': u'tes',
               'limit': 1
            },
            status=200,
        )
        print(response.json)
        assert_equal(len(response.json), 1)


class TestCreateUserApiDisabled(ControllerTestCase):
    '''
    Tests for the creating user when create_user_via_api is disabled.
    '''

    @classmethod
    def setup_class(cls):
        CreateTestData.create()
        cls.sysadmin_user = model.User.get('testsysadmin')
        cls.app = helpers._get_test_app()

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()

    def test_user_create_api_enabled_sysadmin(self):
        params = {
            'name': 'testinganewusersysadmin',
            'email': 'testinganewuser@ckan.org',
            'password': 'TestPassword1',
        }
        res = self.app.post(
            '/api/3/action/user_create',
            json.dumps(params),
            extra_environ={'Authorization': str(self.sysadmin_user.apikey)},
            expect_errors=True)
        res_dict = res.json
        assert res_dict['success'] is True

    def test_user_create_api_disabled_anon(self):
        params = {
            'name': 'testinganewuseranon',
            'email': 'testinganewuser@ckan.org',
            'password': 'TestPassword1',
        }
        res = self.app.post('/api/3/action/user_create', json.dumps(params),
                            expect_errors=True)
        res_dict = res.json
        assert res_dict['success'] is False


class TestCreateUserApiEnabled(ControllerTestCase):
    '''
    Tests for the creating user when create_user_via_api is enabled.
    '''

    @classmethod
    def setup_class(cls):
        CreateTestData.create()
        cls.sysadmin_user = model.User.get('testsysadmin')
        cls.app = helpers._get_test_app()

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()

    def test_user_create_api_enabled_sysadmin(self):
        params = {
            'name': 'testinganewusersysadmin',
            'email': 'testinganewuser@ckan.org',
            'password': 'TestPassword1',
        }
        res = self.app.post(
            '/api/3/action/user_create',
            json.dumps(params),
            extra_environ={'Authorization': str(self.sysadmin_user.apikey)})
        res_dict = res.json
        assert res_dict['success'] is True

    @helpers.change_config('ckan.auth.create_user_via_api', True)
    def test_user_create_api_enabled_anon(self):
        params = {
            'name': 'testinganewuseranon',
            'email': 'testinganewuser@ckan.org',
            'password': 'TestPassword1',
        }
        res = self.app.post('/api/3/action/user_create', json.dumps(params))
        res_dict = res.json
        assert res_dict['success'] is True


class TestCreateUserWebDisabled(ControllerTestCase):
    '''
    Tests for the creating user by create_user_via_web is disabled.
    '''

    @classmethod
    def setup_class(cls):
        CreateTestData.create()
        cls.app = helpers._get_test_app()
        cls.sysadmin_user = model.User.get('testsysadmin')

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()

    @helpers.change_config('ckan.auth.create_user_via_web', False)
    def test_user_create_api_disabled(self):
        params = {
            'name': 'testinganewuser',
            'email': 'testinganewuser@ckan.org',
            'password': 'TestPassword1',
        }
        res = self.app.post('/api/3/action/user_create', json.dumps(params),
                            expect_errors=True)
        res_dict = res.json
        assert res_dict['success'] is False


class TestCreateUserWebEnabled(ControllerTestCase):
    '''
    Tests for the creating user by create_user_via_web is enabled.
    '''

    @classmethod
    def setup_class(cls):
        CreateTestData.create()
        cls.app = helpers._get_test_app()
        cls.sysadmin_user = model.User.get('testsysadmin')

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()

    @helpers.change_config('ckan.auth.create_user_via_web', True)
    def test_user_create_api_disabled(self):
        params = {
            'name': 'testinganewuser',
            'email': 'testinganewuser@ckan.org',
            'password': 'TestPassword1',
        }
        res = self.app.post('/api/3/action/user_create', json.dumps(params),
                            expect_errors=True)
        res_dict = res.json
        assert res_dict['success'] is False


class TestUserActions(object):

    @classmethod
    def setup_class(cls):
        CreateTestData.create()

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()

    def test_user_create_simple(self):
        '''Simple creation of a new user by a non-sysadmin user.'''
        context = {
            'model': model,
            'session': model.Session,
            'user': 'tester'
        }
        data_dict = {
            'name': 'a-new-user',
            'email': 'a.person@example.com',
            'password': 'TestPassword1',
        }

        user_dict = logic.get_action('user_create')(context, data_dict)

        assert_equal(user_dict['name'], 'a-new-user')
        assert 'email' in user_dict
        assert 'apikey' in user_dict
        assert 'password' not in user_dict
