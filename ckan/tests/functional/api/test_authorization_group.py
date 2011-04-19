from nose.tools import assert_equal

from ckan import model
from ckan.lib.create_test_data import CreateTestData
from ckan.tests import TestController as ControllerTestCase
from ckan.tests import url_for

class TestAuthorizationGroupApi(ControllerTestCase):
    @classmethod
    def setup(cls):
        CreateTestData.create()
        for ag_name in [u'anauthzgroup', u'anotherauthzgroup']:
            ag=model.AuthorizationGroup.by_name(ag_name) 
            if not ag: #may already exist, if not create
                ag=model.AuthorizationGroup(name=ag_name)
                model.Session.add(ag)
        model.Session.commit()
                
    @classmethod
    def teardown(cls):
        model.repo.rebuild_db()
        
    def test_autocomplete(self):
        response = self.app.get(
            url=url_for(controller='api', action='authorizationgroup_autocomplete'),
            params={
               'q': u'anauthzgroup',
            },
            status=200,
        )
        print response.json
        assert set(response.json[0].keys()) == set(['id', 'name'])
        assert_equal(response.json[0]['name'], u'anauthzgroup')
        assert_equal(response.header('Content-Type'), 'application/json;charset=utf-8')

    def test_autocomplete_multiple(self):
        response = self.app.get(
            url=url_for(controller='api', action='authorizationgroup_autocomplete'),
            params={
               'q': u'authz',
            },
            status=200,
        )
        print response.json
        assert_equal(len(response.json), 2)

    def test_autocomplete_limit(self):
        response = self.app.get(
            url=url_for(controller='api', action='authorizationgroup_autocomplete'),
            params={
               'q': u'authz',
               'limit': 1
            },
            status=200,
        )
        print response.json
        assert_equal(len(response.json), 1)

