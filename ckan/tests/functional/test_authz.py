import ckan.model as model
from ckan.tests import *

class TestUsage(TestController2):

    @classmethod
    def setup_class(self):
        CreateTestData.create()
        model.Session.remove()

    @classmethod
    def teardown_class(self):
        model.Session.remove()
        model.repo.rebuild_db()
        model.Session.remove()

    def _test_1_visitor_reads(self):
        user = 'visitor'
        res = url_for(controller='package', action='read', id='annakarenina')
        res = self.app.get(offset)
        assert 'annakarenina' in res
