from ckan.tests import *
from ckan.model.harvesting import HarvestSource
from ckan.model.harvesting import HarvestingJob
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

    def test_crud_source(self):
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


class TestHarvestingJob(TestCase):

    def setup(self):
        super(TestHarvestingJob, self).setup()
        source_url = u'http://'
        self.source = HarvestSource(url=source_url)
        model.Session.add(self.source)
        model.Session.commit()
        self.assert_true(self.source.id)
        self.job = None

    def tearDown(self):
        try:
            if self.job:
                self.job.delete()
        finally:
            if self.source:
                self.source.delete()
        model.Session.commit()
        model.Session.remove()
        super(TestHarvestSource, self).teardown()

    def test_crud_job(self):
        self.assert_false(self.job)
        user_ref = u'publisheruser1'
        self.job = HarvestingJob(source=self.source, user_ref=user_ref)
        model.Session.add(self.job)
        model.Session.commit()
        self.assert_true(self.job)
        self.assert_true(self.job.id)
        self.assert_true(self.job.source.id)
        self.assert_equal(self.job.source.id, self.source.id)
        dup = HarvestingJob.get(self.job.id)
        self.job.delete()
        model.Session.commit()
        self.assert_raises(Exception, HarvestSource.get, self.job.id)

