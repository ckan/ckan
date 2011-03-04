import os
from lxml import etree

from nose.plugins.skip import SkipTest

from ckan import model
from ckan.model.harvesting import HarvestSource
from ckan.model.harvesting import HarvestingJob
from ckan.model.harvesting import HarvestedDocument
from ckan.controllers.harvesting import HarvestingJobController

from ckan.tests import *
from ckan.tests.gemini2_examples.expected_values import expect_values0
from ckan.tests.gemini2_examples.expected_values import expect_values1


class HarvesterTestCase(TestCase):

    require_common_fixtures = False

    def setup(self):
        CreateTestData.create()
        self.gemini_example = GeminiExamples()

    def teardown(self):
        model.repo.rebuild_db()


class TestHarvestSource(HarvesterTestCase):

    def test_create_delete_harvest_source(self):
        url = self.gemini_example.url_for(file_index=0)
        source = HarvestSource(url=url)
        source.save()
        source_id = source.id
        source = HarvestSource.get(source_id)
        self.assert_true(source.id)
        self.assert_equal(source.url, url)
        self.delete(source)
        self.commit()
        self.assert_raises(Exception, HarvestSource.get, source_id)

    def test_write_package_and_delete_source(self):
        """Create a package, then ensure that deleting its source
        doesn't delete the package.
        """
        #raise SkipTest('This needs fixing, but JG is going to refactor this. 2011-2-10.')
        url = self.gemini_example.url_for(file_index=0)
        source = HarvestSource(url=url)
        count_before_write = self.count_packages()
        job = HarvestingJob(source=source,
                            user_ref="me")
        controller = HarvestingJobController(job)
        controller.harvest_documents()
        count_after_write = self.count_packages()
        self.assert_equal(count_after_write, count_before_write + 1)
        self.delete_commit(source)
        count_after_delete = self.count_packages()
        self.assert_equal(count_after_delete, count_after_write)

    def _make_package_from_source(self):
        return package, source


class TestHarvestingJob(HarvesterTestCase):

    fixture_user_ref = u'publisheruser1'

    def setup(self):
        super(TestHarvestingJob, self).setup()
        self.source = HarvestSource(
            url=self.gemini_example.url_for(file_index=0)
        )
        self.job = HarvestingJob(
            source=self.source,
            user_ref=self.fixture_user_ref
        )
        self.job.save()
        self.controller = HarvestingJobController(self.job)
        self.job2 = None
        self.source2 = None

    def teardown(self):
        if self.job2:
            self.delete(self.job2)
        if self.source2:
            self.delete(self.source2)
        super(TestHarvestingJob, self).teardown()

    def test_create_and_delete_job(self):
        self.assert_equal(self.job.source_id, self.source.id)
        self.delete_commit(self.job)
        self.assert_raises(Exception, HarvestingJob.get, self.job.id)
        # - check source has not been deleted!
        HarvestSource.get(self.source.id)

    def test_harvest_documents(self):
        before_count = self.count_packages()
        job = self.controller.harvest_documents()
        after_count = self.count_packages()
        self.assert_equal(after_count, before_count + 1)
        self.assert_equal(job.source.documents[0].package.name,
                          (job.report['added'][0]))
        self.assert_true(job.report)
        self.assert_len(job.report['errors'], 0)
        self.assert_len(job.report['added'], 1)

    def test_harvest_documents_twice_unchanged(self):
        job = self.controller.harvest_documents()
        self.assert_len(job.report['errors'], 0)
        self.assert_len(job.report['added'], 1)
        job2 = HarvestingJobController(
            HarvestingJob(
                source=self.source,
                user_ref=self.fixture_user_ref
                )
            ).harvest_documents()
        self.assert_len(job2.report['errors'], 0)
        self.assert_len(job2.report['added'], 0)

    def test_harvest_documents_twice_changed(self):
        job = self.controller.harvest_documents()
        self.assert_len(job.report['errors'], 0)
        self.assert_len(job.report['added'], 1)
        self.source.url = self.gemini_example.url_for(file_index=2)
        self.source.save()
        job2 = HarvestingJobController(
            HarvestingJob(
                source=self.source,
                user_ref=self.fixture_user_ref
                )
            ).harvest_documents()
        self.assert_len(job2.report['errors'], 0)
        self.assert_len(job2.report['added'], 1)

    def test_harvest_documents_source_guid_contention(self):
        job = self.controller.harvest_documents()
        source2 = HarvestSource(
            url=self.gemini_example.url_for(file_index=2),
        )
        # Make sure it has an id by saving it
        source2.save()
        job2 = HarvestingJobController(
            HarvestingJob(
                source=source2,
                user_ref=self.fixture_user_ref
                )
            ).harvest_documents()
        error = job2.report['errors'][0]
        # XXX Should not allow file:// URLs, security implications
        # The one that is conflicting doesn't have a user or publisher set up, otherwise the integers would show here
        assert 'Another source' in error
        assert 'ckan/tests/gemini2_examples/00a743bf-cca4-4c19-a8e5-e64f7edbcadd_gemini2.xml' in error
        assert 'is using metadata GUID 00a743bf-cca4-4c19-a8e5-e64f7edbcadd' in error

    def test_harvest_bad_source_url(self):
        source = HarvestSource(
            url=self.gemini_example.url_for_bad(0)
            )
        job = HarvestingJob(
            source=source,
            user_ref=self.fixture_user_ref
            )
        before_count = self.count_packages()
        self.assert_false(job.report['added'])
        self.assert_false(job.report['errors'])
        job = HarvestingJobController(job).harvest_documents()
        after_count = self.count_packages()
        self.assert_equal(after_count, before_count)
        self.assert_len(job.report['added'], 0)
        self.assert_len(job.report['errors'], 1)
        error = job.report['errors'][0]
        self.assert_contains(error,
                             'Unable to detect source type from content')


class TestHarvesterSourceTypes(HarvesterTestCase):

    fixture_user_ref = u'publisheruser1'

    def setup(self):
        self.gemini_example = GeminiExamples()
        # XXX put real-life CSW examples here if you want, and if they
        # arrive...
        self.sources = [
            (
                'http://127.0.0.1:44444',
                {
                    'errors': ["Error harvesting source: Unable to get content for URL: http://127.0.0.1:44444: URLError(error(111, 'Connection refused'),)"],
                    'packages': 0,
                    'documents': 0,
                },
            ),
            (
                'http://www.google.com',
                {
                    'errors': ["Couldn't find any links to metadata"],
                    'packages': 0,
                    'documents': 0,
                },
            ),
            (
                self.gemini_example.url_for(file_index='index.html'),
                {
                    'errors': [],
                    'packages': 2,
                    'documents': 2,
                },
            ),
        ]
        self.updated_sources = [
            (
                self.gemini_example.url_for(file_index='index.updated.html'),
                {
                    'errors': [],
                    'packages': 2,
                    'documents': 2,
                },
            ),
        ]

    def test_various_sources(self):
        sources = []
        for url, expected in self.sources:
            source = HarvestSource(url=url)
            # Create an ID for it
            source.save()
            sources.append(source)
            job = HarvestingJob(
                source=source,
                user_ref=self.fixture_user_ref
            )
            before_count = self.count_packages()
            self.assert_false(job.report['added'])
            self.assert_false(job.report['errors'])
            job = HarvestingJobController(job).harvest_documents()
            after_count = self.count_packages()
            self.assert_equal(after_count,
                              before_count + expected['packages'])
            for (idx, error) in enumerate(job.report['errors']):
                assert expected['errors'][idx] in error
            # report['added'] is a list, appended to each time a
            # package is touched.
            self.assert_equal(
                len(job.source.documents),
                expected['documents'],
            )
            for (idx, doc) in enumerate(job.source.documents):
                self.assert_true(doc.package)
                assert (doc.package.name in job.report['added'])

        # Now test updated sources
        for url, expected in self.updated_sources:
            sources[-1].url = url
            sources[-1].save()
            job = HarvestingJob(
                # We'll use the last source updated above to test updating a 
                # document
                source=sources[-1],
                user_ref=self.fixture_user_ref
            )
            self.assert_false(job.report['added'])
            self.assert_false(job.report['errors'])
            before_count = self.count_packages()
            before_content = [doc.content for doc in job.source.documents]
            job = HarvestingJobController(job).harvest_documents()
            after_count = self.count_packages()
            after_content = [doc.content for doc in job.source.documents]
            self.assert_true(after_count == before_count == long(expected['packages']))
            # Represents an updated record
            self.assert_equal(len(job.report['added']), 1)
            self.assert_equal(
                len(job.source.documents),
                expected['documents'],
            )
            self.assert_false(before_content == after_content)

class TestHarvestedDocument(HarvesterTestCase):
    def test_create_and_delete_document(self):
        url = self.gemini_example.url_for(0)
        content = self.gemini_example.get_from_url(url)
        document = HarvestedDocument(url=url, content=content)
        document.save()
        document_id = document.id
        self.assert_equal(document.url, url)
        self.assert_equal(document.content, content)
        self.delete_commit(document)
        self.assert_raises(Exception, HarvestedDocument.get, document_id)

    def test_read_values_example0(self):
        self.assert_read_values(0, expect_values0)

    def test_read_values_example1(self):
        self.assert_read_values(1, expect_values1)

    def assert_read_values(self, example_index, expect_values):
        url = self.gemini_example.url_for(file_index=example_index)
        content = self.gemini_example.get_from_url(url)
        document = HarvestedDocument(url=url, content=content)
        values = document.read_values()
        self.assert_gemini_values(values, expect_values)

    def assert_gemini_values(self, values, expect_values):
        for name in expect_values:
            value = values[name]
            expect = expect_values[name]
            self.assert_gemini_value(value, expect, name)

    def assert_gemini_value(self, value, expect, name):
        try:
            self.assert_equal(value, expect)
        except AssertionError, inst:
            msg = "'%s' has unexpected value: %s (expected %s)" %\
                  (name, inst, expect)
            raise AssertionError(msg)


class GeminiExamples(object):
    """Encapsulates the Gemini example files in ckan/tests/gemini2_examples."""

    file_names = [
        u'00a743bf-cca4-4c19-a8e5-e64f7edbcadd_gemini2.xml',
        u'My series sample.xml',
        u'00a743bf-cca4-4c19-a8e5-e64f7edbcadd_gemini2.update.xml',
    ]

    file_names_bad = [
        u'RSS-example.xml',
    ]

    def url_for(self, file_index=None):
        if file_index in [None, 'index.html']:
            name = "index.html"
        elif file_index in ['index.updated.html']:
            name = "index.updated.html"
        else:
            name = self.file_names[file_index]
        path = os.path.join(self.folder_path(), name)
        if not os.path.exists(path):
            raise Exception("Gemini example not found on path: %s" % path)
        return "file://%s" % path

    # Todo: Refactor url_for() and url_for_bad().
    def url_for_bad(self, index=None):
        if index in [None, 'index.html']:
            name = "index.html"
        else:
            name = self.file_names_bad[index]
        path = os.path.join(self.folder_path_bad(), name)
        if not os.path.exists(path):
            raise Exception("Gemini bad example not found on path: %s" % path)
        return "file://%s" % path

    # Todo: Refactor folder_path() and folder_path_bad().
    def folder_path(self):
        from pylons import config
        here_path = config['here']
        return os.path.join(here_path, 'ckan', 'tests', 'gemini2_examples')

    def folder_path_bad(self):
        from pylons import config
        here_path = config['here']
        return os.path.join(here_path, 'ckan', 'tests', 'gemini2_examples_bad')

    def get_from_url(self, url):
        import urllib2
        resource = urllib2.urlopen(url)
        # This returns the raw, data
        data = resource.read()
        # To get it as unicode we need to decode it
        xml = etree.fromstring(data)
        return etree.tostring(xml, encoding=unicode, pretty_print=True)

