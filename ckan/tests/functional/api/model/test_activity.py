from ckan.tests.functional.api.base import BaseModelApiTestCase
from ckan.tests.functional.api.base import Api2TestCase
import ckan.model as model

class TestActivity(Api2TestCase,BaseModelApiTestCase):

    def setup(self):
        super(TestActivity, self).setup()

    def teardown(self):
        super(TestActivity, self).teardown()

    def test_activity(self):
        tester = model.Session.query(model.user.User).filter_by(name="tester").first()
        result = self.app.get("/api/1/rest/activity/%s" % tester.id, status=self.STATUS_200_OK)
        data = self.loads(result.body)
        assert len(data) == 2
        for event in data:
            assert event['user_id'] == tester.id

