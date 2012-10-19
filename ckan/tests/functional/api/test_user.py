from nose.tools import assert_equal

import ckan.logic as logic
from ckan import model
from ckan.lib.create_test_data import CreateTestData
from ckan.tests import TestController as ControllerTestCase
from ckan.tests import url_for

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
        print response.json
        assert set(response.json[0].keys()) == set(['id', 'name', 'fullname'])
        assert_equal(response.json[0]['name'], u'testsysadmin')
        assert_equal(response.header('Content-Type'), 'application/json;charset=utf-8')

    def test_autocomplete_multiple(self):
        response = self.app.get(
            url=url_for(controller='api', action='user_autocomplete', ver=2),
            params={
               'q': u'tes',
            },
            status=200,
        )
        print response.json
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
        print response.json
        assert_equal(len(response.json), 1)

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
            'password': 'supersecret',
        }

        user_dict = logic.get_action('user_create')(context, data_dict)

        assert_equal(user_dict['name'], 'a-new-user')
        assert 'email' in user_dict
        assert 'apikey' in user_dict
        assert 'password' not in user_dict

    def test_user_update_simple(self):
        '''Simple update of a user by themselves.'''
        context = {
            'model': model,
            'session': model.Session,
            'user': 'annafan',
        }

        data_dict = {
            'id': 'annafan',
            'email': 'anna@example.com',
        }

        user_dict = logic.get_action('user_update')(context, data_dict)

        assert_equal(user_dict['email'], 'anna@example.com')
        assert 'apikey' in user_dict
        assert 'password' not in user_dict

