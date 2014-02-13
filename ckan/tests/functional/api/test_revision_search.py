from ckan.tests.functional.api.base import *
from ckan.tests import TestController as ControllerTestCase

class RevisionSearchApiTestCase(ApiTestCase, ControllerTestCase):

    @classmethod
    def setup_class(self):
        CreateTestData.create()

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()

    def test_12_search_revision_bad_requests(self):
        offset = self.offset('/search/revision')
        # Check bad request.
        res = self.app.get(offset, status=400)
        self.assert_json_response(res, 'Bad request - Missing search term')
        res = self.app.get(offset+'?since_rev=2010-01-01T00:00:00', status=400)
        self.assert_json_response(res, 'Bad request - Missing search term')
        res = self.app.get(offset+'?since_revision=2010-01-01T00:00:00', status=400)
        self.assert_json_response(res, 'Bad request - Missing search term')
        res = self.app.get(offset+'?since_id=', status=400)
        self.assert_json_response(res, 'Bad request - No revision specified')
        res = self.app.get(offset+'?since_id=1234', status=404)
        self.assert_json_response(res, 'Not found - There is no revision')

    def test_12_search_revision_since_rev(self):
        offset = self.offset('/search/revision')
        revs = model.Session.query(model.Revision).all()
        rev_first = revs[-1]
        params = "?since_id=%s" % rev_first.id
        res = self.app.get(offset+params, status=200)
        res_list = self.data_from_res(res)
        assert rev_first.id not in res_list
        for rev in revs[:-1]:
            assert rev.id in res_list, (rev.id, res_list)
        rev_last = revs[0]
        params = "?since_id=%s" % rev_last.id
        res = self.app.get(offset+params, status=200)
        res_list = self.data_from_res(res)
        assert res_list == [], res_list

    def test_12_search_revision_since_time(self):
        offset = self.offset('/search/revision')
        revs = model.Session.query(model.Revision).all()
        # Check since time of first.
        rev_first = revs[-1]
        params = "?since_time=%s" % rev_first.timestamp.isoformat()
        res = self.app.get(offset+params, status=200)
        res_list = self.data_from_res(res)
        assert rev_first.id not in res_list
        for rev in revs[:-1]:
            assert rev.id in res_list, (rev.id, res_list)
        # Check since time of last.
        rev_last = revs[0]
        params = "?since_time=%s" % rev_last.timestamp.isoformat()
        res = self.app.get(offset+params, status=200)
        res_list = self.data_from_res(res)
        assert res_list == [], res_list
        # Check bad format.
        params = "?since_time=2010-04-31T23:45"
        res = self.app.get(offset+params, status=400)
        self.assert_json_response(res, 'Bad request - ValueError: day is out of range for month')


class TestRevisionSearchApi1(Api1TestCase, RevisionSearchApiTestCase): pass
class TestRevisionSearchApi2(Api2TestCase, RevisionSearchApiTestCase): pass
