from ckan.tests import *
from ckan.model.harvesting import HarvestSource
import ckan.model as model

class TestCase(object):

    def setup(self):
        model.repo.clean_db()
        model.repo.rebuild_db()
        model.Session.remove()

    def teardown(self):
        model.repo.clean_db()
        model.Session.remove()

    def assert_true(self, value):
        assert value, "Not true: '%s'" % value

    def assert_false(self, value):
        assert not value, "Not false: '%s'" % value

    def assert_equal(self, value1, value2):
        assert value1 == value2, "Not equal: %s" % ((value1, value2),)

    def assert_isinstance(self, value, check):
        assert isinstance(value, check), "Not an instance: %s" % ((value, check),)
    
    def assert_raises(self, exception_class, callable, *args, **kwds): 
        try:
            callable(*args, **kwds)
        except exception_class:
            pass
        else:
            assert False, "Didn't raise '%s' when calling: %s with %s" % (exception_class, callable, (args, kwds))


class TestHarvestSource(TestCase):

    def setup(self):
        super(TestHarvestSource, self).setup()
        self.source = None

    def tearDown(self):
        if self.source:
            self.source.delete()
        model.Session.commit()
        model.Session.remove()
        super(TestHarvestSource, self).teardown()

    def test_crud(self):
        self.assert_false(self.source)
        fixture_url = u'http://'
        self.source = HarvestSource(url=fixture_url)
        model.Session.add(self.source)
        model.Session.commit()
        self.assert_true(self.source)
        self.assert_true(self.source.id)
        dup = HarvestSource.get(self.source.id)
        self.source.delete()
        model.Session.commit()
        self.assert_raises(Exception, HarvestSource.get, self.source.id)

