from nose.tools import assert_equal

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
            url=url_for(controller='api', action='user_autocomplete'),
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
            url=url_for(controller='api', action='user_autocomplete'),
            params={
               'q': u'tes',
            },
            status=200,
        )
        print response.json
        assert_equal(len(response.json), 2)

    def test_autocomplete_limit(self):
        response = self.app.get(
            url=url_for(controller='api', action='user_autocomplete'),
            params={
               'q': u'tes',
               'limit': 1
            },
            status=200,
        )
        print response.json
        assert_equal(len(response.json), 1)

