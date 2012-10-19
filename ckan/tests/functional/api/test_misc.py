from paste.deploy.converters import asbool
from ckan.tests.functional.api.base import *
from ckan.lib.create_test_data import CreateTestData
from ckan.tests import TestController as ControllerTestCase

class MiscApiTestCase(ApiTestCase, ControllerTestCase):

    @classmethod
    def setup_class(self):
        CreateTestData.create()

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()

    # Todo: Move this method to the Model API?
    def test_0_tag_counts(self):
        offset = self.offset('/tag_counts')
        res = self.app.get(offset, status=200)
        results = self.loads(res.body)
        assert [u'Flexible \u30a1', 2] in results, results
        assert ["russian", 2] in results, results
        assert ["tolstoy", 1] in results, results

class QosApiTestCase(ApiTestCase, ControllerTestCase):

    def test_throughput(self):
        if not asbool(config.get('ckan.enable_call_timing', "false")):
            raise SkipTest
        # Create some throughput.
        import datetime
        start = datetime.datetime.now()
        offset = self.offset('/rest/package')
        while datetime.datetime.now() - start < datetime.timedelta(0,10):
            res = self.app.get(offset, status=[200])
        # Check throughput.
        offset = self.offset('/qos/throughput/')
        res = self.app.get(offset, status=[200])
        data = self.data_from_res(res)
        throughput = float(data)
        assert throughput > 1, throughput

class TestMiscApi1(Api1TestCase, MiscApiTestCase): pass
class TestQosApi1(Api1TestCase, QosApiTestCase): pass
class TestMiscApi2(Api2TestCase, MiscApiTestCase): pass
class TestQosApi2(Api2TestCase, QosApiTestCase): pass
class TestMiscApiUnversioned(ApiUnversionedTestCase, MiscApiTestCase): pass
class TestQosApiUnversioned(ApiUnversionedTestCase, QosApiTestCase): pass
