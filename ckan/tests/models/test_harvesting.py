import os
from ckan.tests import *
from ckan.model.harvesting import HarvestSource
from ckan.model.harvesting import HarvestingJob
from ckan.model.harvesting import HarvestedDocument
import ckan.model as model

class Gemini2Examples(object):
    """Encapsulates the Gemini2 example files in ckan/tests/gemini2_examples."""

    gemini2_examples = [
        u'00a743bf-cca4-4c19-a8e5-e64f7edbcadd_gemini2.xml',
        u'My series sample.xml',
    ]

    def gemini2_examples_path(self):
        from pylons import config
        here_path = config['here']
        examples_path = os.path.join(here_path, 'ckan', 'tests', 'gemini2_examples')
        return examples_path

    def gemini2_url(self, index):
        name = self.gemini2_examples[index]
        path = os.path.join(self.gemini2_examples_path(), name)
        if not os.path.exists(path):
            raise Exception, "Gemini2 example not found on path: %s" % path
        return "file://%s" % path

    def gemini2_content(self, url):
        import urllib2
        resource = urllib2.urlopen(url)
        content = resource.read()
        return content


class TestCase(CheckMethods, ModelMethods, Gemini2Examples):

    def setup(self):
        self.dropall()
        self.rebuild()
        self.remove()

    def teardown(self):
        self.dropall()
        self.remove()

    def create_fixture(self, domain_type, **kwds):
        # Create and check new fixture.
        object = domain_type.create_save(**kwds)
        self.assert_true(object.id)
        return object

    def create_harvested_document(self, **kwds):
        return self.create_fixture(HarvestedDocument, **kwds)
 
    def create_harvest_source(self, **kwds):
        return self.create_fixture(HarvestSource, **kwds)

    def create_harvesting_job(self, **kwds):
        return self.create_fixture(HarvestingJob, **kwds)


class TestHarvestSource(TestCase):

    def setup(self):
        super(TestHarvestSource, self).setup()
        self.source = None
        self.document = None

    def teardown(self):
        if self.source:
            self.delete(self.source)
        self.commit_remove()
        if self.document:
            self.delete(self.document)
        self.commit_remove()
        super(TestHarvestSource, self).teardown()

    def test_crud_source(self):
        self.assert_false(self.source)
        url = self.gemini2_url(0)
        self.source = self.create_harvest_source(url=url)
        self.assert_true(self.source)
        self.assert_true(self.source.id)
        dup = HarvestSource.get(self.source.id)
        self.delete_commit(self.source)
        self.assert_raises(Exception, HarvestSource.get, self.source.id)

    def test_write_package(self):
        url = self.gemini2_url(0)
        content = self.gemini2_content(url)
        self.document = self.create_harvested_document(url=url, content=content)
        self.source = self.create_harvest_source(url=url)
        count_before = self.count_packages()
        assert self.source.write_package(self.document)
        self.delete_commit(self.source)
        count_after = self.count_packages()
        self.assert_equal(count_after, count_before + 1)


class TestHarvestingJob(TestCase):

    def setup(self):
        super(TestHarvestingJob, self).setup()
        url = self.gemini2_url(0)
        self.source = self.create_harvest_source(url=url)
        self.job = None

    def teardown(self):
        try:
            if self.job:
                self.delete_commit(self.job)
        finally:
            if self.source:
                pass #self.delete_commit(self.source)
        super(TestHarvestingJob, self).teardown()

    def test_crud_job(self):
        self.assert_false(self.job)
        user_ref = u'publisheruser1'
        self.assert_true(self.source.id)
        self.job = self.create_harvesting_job(source=self.source, user_ref=user_ref)
        self.assert_true(self.job)
        self.assert_true(self.job.id)
        self.assert_true(self.job.source_id)
        self.assert_true(self.job.source)
        self.assert_equal(self.job.source_id, self.source.id)
        dup = HarvestingJob.get(self.job.id)
        self.delete_commit(self.job)
        self.assert_raises(Exception, HarvestSource.get, self.job.id)
        dup = HarvestSource.get(self.source.id)

    def test_harvest_documents(self):
        self.assert_false(self.job)
        user_ref = u'publisheruser2'
        count_before = self.count_packages()
        self.job = self.create_harvesting_job(source=self.source, user_ref=user_ref)
        self.job.harvest_documents()
        count_after = self.count_packages()
        self.assert_equal(count_after, count_before + 1)


class TestHarvestedDocument(TestCase):

    def setup(self):
        super(TestHarvestedDocument, self).setup()
        self.document = None

    def teardown(self):
        if self.document:
            self.delete_commit(self.document)
        super(TestHarvestedDocument, self).teardown()

    def test_crud_document(self):
        self.assert_false(self.document)
        url = self.gemini2_url(0)
        content = self.gemini2_content(url)
        self.document = self.create_harvested_document(url=url, content=content)
        self.assert_true(self.document)
        self.assert_true(self.document.id)
        self.assert_true(self.document.url)
        dup = HarvestedDocument.get(self.document.id)
        self.delete_commit(self.document)
        self.assert_raises(Exception, HarvestSource.get, self.document.id)

    def test_read_attributes(self):
        url = self.gemini2_url(0)
        content = self.gemini2_content(url)
        self.document = self.create_harvested_document(url=url, content=content)
        self.assert_true(self.document.id)
        data = self.document.read_attributes()
        self.assert_equal(data['guid'], ['00a743bf-cca4-4c19-a8e5-e64f7edbcadd'])

