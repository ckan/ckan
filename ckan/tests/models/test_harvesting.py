from ckan.tests import *
from ckan.model.harvesting import HarvestSource
from ckan.model.harvesting import HarvestingJob
import ckan.model as model

class ModelMethods(object):

    def dropall(self):
        model.repo.clean_db()

    def rebuild(self):
        model.repo.rebuild_db()
        self.remove()

    def add(self, domain_object):
        model.Session.add(domain_object)

    def add_commit(self, domain_object):
        self.add(domain_object)
        self.commit()

    def add_commit_remove(self, domain_object):
        self.add(domain_object)
        self.commit_remove()

    def delete(self, domain_object):
        model.Session.delete(domain_object)

    def delete_commit(self, domain_object):
        self.delete(domain_object)
        self.commit()

    def delete_commit_remove(self, domain_object):
        self.delete(domain_object)
        self.commit()

    def commit(self):
        model.Session.commit()

    def commit_remove(self):
        self.commit()
        self.remove()

    def remove(self):
        model.Session.remove()


class CheckMethods(object):

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


class TestCase(CheckMethods, ModelMethods):

    def setup(self):
        self.dropall()
        self.rebuild()
        self.remove()

    def teardown(self):
        model.repo.clean_db()
        self.remove()


class TestHarvestSource(TestCase):

    def setup(self):
        super(TestHarvestSource, self).setup()
        self.source = None

    def teardown(self):
        if self.source:
            self.delete(self.source)
        self.commit_remove()
        super(TestHarvestSource, self).teardown()

    def test_crud_source(self):
        self.assert_false(self.source)
        fixture_url = u'http://'
        self.source = HarvestSource(url=fixture_url)
        self.add_commit(self.source)
        self.assert_true(self.source)
        self.assert_true(self.source.id)
        dup = HarvestSource.get(self.source.id)
        self.delete_commit(self.source)
        self.assert_raises(Exception, HarvestSource.get, self.source.id)


class TestHarvestingJob(TestCase):

    def setup(self):
        super(TestHarvestingJob, self).setup()
        source_url = u'http://'
        self.source = HarvestSource(url=source_url)
        self.add_commit(self.source)
        self.assert_true(self.source.id)
        self.job = None

    def teardown(self):
        try:
            if self.job:
                self.delete_commit(self.job)
        finally:
            if self.source:
                self.delete_commit(self.source)
        super(TestHarvestingJob, self).teardown()

    def create_harvesting_job(self, source, user_ref):
        return HarvestingJob.create_record(model.Session,
            source=source, user_ref=user_ref)
 
    def test_crud_job(self):
        self.assert_false(self.job)
        user_ref = u'publisheruser1'
        self.job = self.create_harvesting_job(source=self.source, user_ref=user_ref)
        self.assert_true(self.job)
        self.assert_true(self.job.id)
        self.assert_true(self.job.source.id)
        self.assert_equal(self.job.source.id, self.source.id)
        dup = HarvestingJob.get(self.job.id)
        self.delete_commit(self.job)
        self.assert_raises(Exception, HarvestSource.get, self.job.id)

