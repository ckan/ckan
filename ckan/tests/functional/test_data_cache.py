import json
import datetime
from nose.tools import assert_equal

from ckan.tests.pylons_controller import TestController, PylonsTestCase
import ckan.model as model


class TestDataCache(TestController, PylonsTestCase):
    @classmethod
    def setup_class(cls):
        model.repo.init_db()

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()

    @classmethod
    def _was_just_now(cls, time):
        assert (datetime.datetime.now() - time) < datetime.timedelta(minutes=1)

    def test_simple(self):
        model.DataCache.set("1234", "test_key", "some_value")
        val, when = model.DataCache.get("1234", "test_key")
        self._was_just_now(when)
        assert_equal("some_value", val)

    def test_fail_no_object_id(self):
        is_set = model.DataCache.set(None, "test_key", "some_value")
        assert_equal(is_set, False)

    def test_fail_no_key(self):
        is_set = model.DataCache.set("1234", None, "some_value")
        assert_equal(is_set, False)

    def test_fail_no_data(self):
        is_set = model.DataCache.set("1234", "test_key", None)
        assert_equal(is_set, True)
        val, when = model.DataCache.get("1234", "test_key")
        assert_equal(None, val)

    def test_store_int(self):
        is_set = model.DataCache.set("1234", "test_key", 101)
        assert_equal(is_set, True)
        val, when = model.DataCache.get("1234", "test_key")
        self._was_just_now(when)
        assert_equal(101, int(val))

    def test_store_simple_json(self):
        l = [1,2,3,4]

        is_set = model.DataCache.set("1234", "test_key", json.dumps(l))
        assert_equal(is_set, True)
        val, when = model.DataCache.get("1234", "test_key")
        self._was_just_now(when)
        assert_equal(l, json.loads(val))

    def test_store_slightly_lesssimple_json(self):
        import datetime
        d = {'values': [1,2,3,4], 'when': datetime.datetime.now().isoformat()}

        is_set = model.DataCache.set("1234", "test_key", json.dumps(d))
        assert_equal(is_set, True)
        val, when = model.DataCache.get("1234", "test_key")
        self._was_just_now(when)
        assert_equal(d, json.loads(val))

    def test_store_complex_json(self):
        import datetime
        d = {'values': [1,2,3,4],
             'when': datetime.datetime.now(),
             'extra': {'rows':[]}}
        for x in xrange(10):
            d['extra']['rows'].append('A row of data to be used somewhere')

        is_set = model.DataCache.set("1234", "test_key", d, convert_json=True)
        assert_equal(is_set, True)
        val, when = model.DataCache.get("1234", "test_key", convert_json=True)
        self._was_just_now(when)
        assert_equal(d, val)

