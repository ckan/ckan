import os

from nose.plugins.skip import SkipTest

from ckan.tests import *
from ckan.model.harvesting import HarvestSource
from ckan.model.harvesting import HarvestingJob
from ckan.model.harvesting import HarvestedDocument
from ckan.model.harvesting import decode_response
import ckan.model as model

class HarvesterTestCase(TestCase):

    require_common_fixtures = False

    def setup(self):
        # XXX what's the proper way to ensure the Harvesting tables
        # get set up?
        from ckan.model.harvesting import metadata
        metadata.create_all(bind=metadata.bind)
        super(HarvesterTestCase, self).setup()
        self.source = None
        self.job = None
        self.document = None
        self.gemini = GeminiExamples()

    def teardown(self):
        if self.document:
            self.delete(self.document)
        for document in HarvestedDocument.filter():
            document.delete()
        if self.job:
            self.delete(self.job)
        if self.source:
            self.delete(self.source)
        self.commit_remove()
        self.purge_package_by_name('00a743bf-cca4-4c19-a8e5-e64f7edbcadd')
        super(HarvesterTestCase, self).teardown()

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


class TestHarvestSource(HarvesterTestCase):

    def test_crud_source(self):
        self.assert_false(self.source)
        url = self.gemini.url_for(0)
        source = self.create_harvest_source(url=url)
        self.assert_true(source)
        source_id = source.id
        self.assert_true(source_id)
        # Drop reference to make sure we get a fresh instance.
        source = None  
        source = HarvestSource.get(source_id)
        self.assert_true(source.id)
        self.assert_true(source.url)
        self.assert_equal(source.url, url)
        self.delete_commit(source)
        self.assert_raises(Exception, HarvestSource.get, source_id)

    def test_write_package(self):
        url = self.gemini.url_for(0)
        content = self.gemini.get_content(url)
        self.source = self.create_harvest_source(url=url)
        count_before = self.count_packages()
        assert self.source.write_package(content=content)
        count_after = self.count_packages()
        self.assert_equal(count_after, count_before + 1)
        self.delete_commit(self.source)
        count_after_delete = self.count_packages()
        self.assert_equal(count_after_delete, count_after)


class TestHarvestingJob(HarvesterTestCase):

    fixture_user_ref = u'publisheruser1'

    def setup(self):
        super(TestHarvestingJob, self).setup()
        self.assert_false(self.source)
        self.source = self.create_harvest_source(
            url=self.gemini.url_for(0)
        )
        self.assert_true(self.source.id)
        self.assert_false(self.job)
        self.job = self.create_harvesting_job(
            source=self.source, 
            user_ref=self.fixture_user_ref
        )
        self.job2 = None
        self.source2 = None

    def teardown(self):
        if self.job2:
            self.delete(self.job2)
        if self.source2:
            self.delete(self.source2)
        super(TestHarvestingJob, self).teardown()

    def test_crud_job(self):
        # Create.
        self.assert_true(self.job)
        self.assert_true(self.job.id)
        self.assert_true(self.job.source_id)
        self.assert_true(self.job.source)
        self.assert_equal(self.job.source_id, self.source.id)
        # Read.
        dup = HarvestingJob.get(self.job.id)
        # Todo: Update.
        # Delete.
        self.delete_commit(self.job)
        self.assert_raises(Exception, HarvestingJob.get, self.job.id)
        # - check source has not been deleted!
        HarvestSource.get(self.source.id)

    def test_harvest_documents(self):
        before_count = self.count_packages()
        self.job.harvest_documents()
        after_count = self.count_packages()
        self.assert_equal(after_count, before_count + 1)
        assert self.job.source.documents
        assert self.job.source.documents[0].package
        self.assert_true(self.job.report)
        self.assert_len(self.job.report['errors'], 0)
        self.assert_len(self.job.report['packages'], 1)
        self.assert_equal(self.job.source.documents[0].package.id, (self.job.report['packages'][0]))

    def test_harvest_documents_twice_unchanged(self):
        self.job.harvest_documents()
        self.assert_len(self.job.report['errors'], 0)
        self.assert_len(self.job.report['packages'], 1)
        self.job2 = self.create_harvesting_job(
            source=self.source, 
            user_ref=self.fixture_user_ref
        )
        self.job2.harvest_documents()
        self.assert_len(self.job2.report['errors'], 0)
        self.assert_len(self.job2.report['packages'], 0)

    def test_harvest_documents_twice_changed(self):
        self.job.harvest_documents()
        self.assert_len(self.job.report['errors'], 0)
        self.assert_len(self.job.report['packages'], 1)
        self.source.url = self.gemini.url_for(2)
        self.source.save()
        self.job2 = self.create_harvesting_job(
            source=self.source, 
            user_ref=self.fixture_user_ref
        )
        self.job2.harvest_documents()
        self.assert_len(self.job2.report['errors'], 0)
        self.assert_len(self.job2.report['packages'], 1)

    def test_harvest_documents_source_guid_contention(self):
        self.job.harvest_documents()
        self.assert_len(self.job.report['errors'], 0)
        self.assert_len(self.job.report['packages'], 1)
        self.source2 = self.create_harvest_source(
            url=self.gemini.url_for(2)
        )
        self.job2 = self.create_harvesting_job(
            source=self.source2,
            user_ref=self.fixture_user_ref
        )
        self.job2.harvest_documents()
        self.assert_len(self.job2.report['packages'], 0)
        self.assert_len(self.job2.report['errors'], 1)
        error = self.job2.report['errors'][0]
        self.assert_contains(error, "Another source is using metadata GUID")


class TestHarvestingJobRssFeed(HarvesterTestCase):

    fixture_user_ref = u'publisheruser1'

    def setup(self):
        super(TestHarvestingJobRssFeed, self).setup()
        self.assert_false(self.source)
        self.source = self.create_harvest_source(
            url=self.gemini.url_for_bad(0)
        )
        self.assert_true(self.source.id)
        self.assert_false(self.job)
        self.job = self.create_harvesting_job(
            source=self.source, 
            user_ref=self.fixture_user_ref
        )

    def test_harvest_documents_from_rss(self):
        before_count = self.count_packages()
        self.assert_false(self.job.report)
        self.job.harvest_documents()
        after_count = self.count_packages()
        self.assert_equal(after_count, before_count)
        self.assert_true(self.job.report)
        self.assert_len(self.job.report['packages'], 0)
        self.assert_len(self.job.report['errors'], 1)
        error = self.job.report['errors'][0]
        self.assert_contains(error, 'Unable to detect source type from content')


class TestHarvestWafSource(HarvesterTestCase):

    fixture_user_ref = u'publisheruser1'

    def setup(self):
        super(TestHarvestWafSource, self).setup()
        self.assert_false(self.source)
        self.source = self.create_harvest_source(
            url=self.gemini.url_for('index.html')
        )
        self.assert_true(self.source.id)
        self.assert_false(self.job)
        self.job = self.create_harvesting_job(
            source=self.source, 
            user_ref=self.fixture_user_ref
        )

    def test_harvest_documents_from_waf(self):
        before_count = self.count_packages()
        self.assert_false(self.job.report)
        self.job.harvest_documents()
        self.assert_len(self.job.report['errors'], 0)
        self.assert_len(self.job.report['packages'], 3)
        self.assert_len(self.job.source.documents, 2)
        self.assert_true(self.job.source.documents[0].package)
        self.assert_true(self.job.source.documents[1].package)
        self.assert_equal(self.job.source.documents[0].package.id, (self.job.report['packages'][0]))
        self.assert_equal(self.job.source.documents[1].package.id, (self.job.report['packages'][1]))
        after_count = self.count_packages()
        self.assert_equal(after_count, before_count + 2)




class TestHarvestCswSource(HarvesterTestCase):

    fixture_user_ref = u'publisheruser1'

    def setup(self):
        super(TestHarvestCswSource, self).setup()
        self.assert_false(self.source)
        from pylons import config
        base_url=config.get('example_csw_url', '')
        if not base_url:
            raise SkipTest
        self.source = self.create_harvest_source(
            url=base_url,
        )
        self.job = self.create_harvesting_job(
            source=self.source, 
            user_ref=self.fixture_user_ref
        )

    def test_harvest_documents_from_csw(self):
        before_count = self.count_packages()
        self.assert_false(self.job.report)
        self.job.harvest_documents()
        after_count = self.count_packages()
        self.assert_equal(after_count, before_count + 1)
        assert self.job.source.documents
        assert self.job.source.documents[0].package
        self.assert_true(self.job.report)
        self.assert_len(self.job.report['errors'], 0)
        self.assert_len(self.job.report['packages'], 1)
        self.assert_equal(self.job.source.documents[0].package.id, (self.job.report['packages'][0]))


class TestHarvestCswSourceDown(HarvesterTestCase):

    fixture_user_ref = u'publisheruser1'

    def setup(self):
        super(TestHarvestCswSourceDown, self).setup()
        self.assert_false(self.source)
        base_url = 'http://127.0.0.1:44444'
        self.source = self.create_harvest_source(
            url=base_url,
        )
        self.job = self.create_harvesting_job(
            source=self.source, 
            user_ref=self.fixture_user_ref
        )

    def test_harvest_documents_from_csw(self):
        before_count = self.count_packages()
        self.assert_false(self.job.report)
        self.job.harvest_documents()
        after_count = self.count_packages()
        self.assert_equal(after_count, before_count)
        self.assert_true(self.job.report)
        self.assert_len(self.job.report['packages'], 0)
        self.assert_len(self.job.report['errors'], 1)
        error = self.job.report['errors'][0]
        self.assert_contains(error, 'Unable to get content for URL')


class TestHarvestCswSourceRandomWebsite(HarvesterTestCase):

    fixture_user_ref = u'publisheruser1'

    def setup(self):
        super(TestHarvestCswSourceRandomWebsite, self).setup()
        self.assert_false(self.source)
        base_url = 'http://www.fsf.org'
        self.source = self.create_harvest_source(
            url=base_url,
        )
        self.job = self.create_harvesting_job(
            source=self.source, 
            user_ref=self.fixture_user_ref,
        )

    def test_harvest_documents_from_csw(self):
        before_count = self.count_packages()
        self.assert_false(self.job.report)
        self.job.harvest_documents()
        error = self.job.report['errors'][0]
        if "timeout" in error or "service not known" in error:
            raise SkipTest("Couldn't connect to internet for test")
        after_count = self.count_packages()
        self.assert_equal(after_count, before_count)
        self.assert_true(self.job.report)
        self.assert_len(self.job.report['packages'], 0)
        self.assert_len(self.job.report['errors'], 1)
        self.assert_contains(error, "Couldn't find any links to metadata files.")


class TestHarvestedDocument(HarvesterTestCase):

    expect_values0 = {
        'guid': '00a743bf-cca4-4c19-a8e5-e64f7edbcadd',
        'metadata-language': 'eng',
        'resource-type': 'dataset',
        'metadata-point-of-contact': [{'contact-info': {'email': 'gis@barrowbc.gov.uk'}, 'organisation-name': 'Barrow Borough Council', 'role': 'pointOfContact', 'position-name': ''}],
        'metadata-date': '2009-10-16',
        'spatial-reference-system': '<gmd:MD_ReferenceSystem xmlns:gmd="http://www.isotc211.org/2005/gmd" xmlns:gco="http://www.isotc211.org/2005/gco" xmlns:gml="http://www.opengis.net/gml/3.2" xmlns:xlink="http://www.w3.org/1999/xlink"><gmd:referenceSystemIdentifier><gmd:RS_Identifier><gmd:code><gco:CharacterString>urn:ogc:def:crs:EPSG::27700</gco:CharacterString></gmd:code></gmd:RS_Identifier></gmd:referenceSystemIdentifier></gmd:MD_ReferenceSystem>',
        'title': 'Council Owned Litter Bins',
        'alternative-title': [],
        'dataset-reference-date': [
            {
                'type': 'creation',
                'value': '2008-10-10',
            },{
                'type': 'revision',
                'value': '2009-10-08',
            },
        ],
        'date-released': '',
        'date-updated': '2009-10-08',
        'unique-resource-identifier': '<gmd:RS_Identifier xmlns:gmd="http://www.isotc211.org/2005/gmd" xmlns:gco="http://www.isotc211.org/2005/gco" xmlns:gml="http://www.opengis.net/gml/3.2" xmlns:xlink="http://www.w3.org/1999/xlink"><gmd:code><gco:CharacterString>BBC:000006</gco:CharacterString></gmd:code><gmd:codeSpace><gco:CharacterString>Barrow Borough Council</gco:CharacterString></gmd:codeSpace></gmd:RS_Identifier>',
        'abstract': 'Location of Council owned litter bins within Borough.',
        'responsible-organisation': [
            {
                'contact-info': {
                        'email': 'gis@barrowbc.gov.uk',
                },
                'organisation-name': 'Barrow Borough Council',
                'role': 'pointOfContact',
                'position-name': ''
            }
        ],
        'publisher': '',
        'contact': 'Barrow Borough Council',
        'contact-email': 'gis@barrowbc.gov.uk',
        'frequency-of-update': 'unknown',
        'keyword-inspire-theme': ['Utility and governmental services'],
        'keyword-controlled-other': ['Utility and governmental services'],
        'keyword-free-text': [],
        'tags': ['Utility and governmental services'],
        'limitations-on-public-access': [],
        'use-constraints': ['conditions unknown'],
        'spatial-data-service-type': '',
        'spatial-resolution': '',
        'equivalent-scale': ['1250'],
        'dataset-language': ['eng'],
        'topic-category': ['environment'],
        'extent-controlled': [],
        'extent-free-text': [],
        'bbox-west-long': '-3.32485',
        'bbox-east-long': '-3.12442',
        'bbox-north-lat': '54.218407',
        'bbox-south-lat': '54.039634',
        'temporal-extent-begin': '1977-03-10T11:45:30',
        'temporal-extent-end': '2005-01-15T09:10:00',
        'vertical-extent': '',
        'coupled-resource': [],
        'additional-information-source': '',
        'data-format': [
            {'version': '', 'name': ''}
        ],
        'resource-locator': [
            {
                'url': 'http://www.barrowbc.gov.uk',
                'function': '',
            }
        ],
        'url': '',
        'conformity-specification': '',
        'conformity-pass': '',
        'conformity-explanation': '',
        'lineage': 'Dataset created from ground surveys using Ordnance Survey Mastemap as base.',
    }

    expect_values1 = {
        'guid': '603f921c-79df-4866-ac69-f4acc37e4851',
        'metadata-language': 'eng',
        'resource-type': 'series',
        'metadata-point-of-contact': [{'contact-info': {'email': 'customerservices@ordnancesurvey.co.uk'}, 'organisation-name': 'Ordnance Survey', 'role': 'publisher', 'position-name': 'Customer services'}],
        'metadata-date': '2010-08-19T17:05:15',
        'spatial-reference-system': '<gmd:MD_ReferenceSystem xmlns:gmd="http://www.isotc211.org/2005/gmd" xmlns:gts="http://www.isotc211.org/2005/gts" xmlns:gml="http://www.opengis.net/gml/3.2" xmlns:gmx="http://www.isotc211.org/2005/gmx" xmlns:gsr="http://www.isotc211.org/2005/gsr" xmlns:gss="http://www.isotc211.org/2005/gss" xmlns:gco="http://www.isotc211.org/2005/gco" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><gmd:referenceSystemIdentifier><gmd:RS_Identifier><gmd:code><gco:CharacterString>urn:ogc:def:crs:EPSG::4258</gco:CharacterString></gmd:code></gmd:RS_Identifier></gmd:referenceSystemIdentifier></gmd:MD_ReferenceSystem>',
        'title': u'OS MasterMap\xae Imagery Layer',
        'alternative-title': [],
        'dataset-reference-date': [
            {
                'type': 'creation',
                'value': '2004-09-15T16:13:00',
            },
        ],
        'date-released': '',
        'date-updated': '',
        'unique-resource-identifier': '<gmd:RS_Identifier xmlns:gmd="http://www.isotc211.org/2005/gmd" xmlns:gts="http://www.isotc211.org/2005/gts" xmlns:gml="http://www.opengis.net/gml/3.2" xmlns:gmx="http://www.isotc211.org/2005/gmx" xmlns:gsr="http://www.isotc211.org/2005/gsr" xmlns:gss="http://www.isotc211.org/2005/gss" xmlns:gco="http://www.isotc211.org/2005/gco" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><gmd:code><gco:CharacterString>OSMM Imagery</gco:CharacterString></gmd:code><gmd:codeSpace><gco:CharacterString>http://www.ordnancesurvey.co.uk</gco:CharacterString></gmd:codeSpace></gmd:RS_Identifier>',
        'abstract': u'High resolution, national, fully Orthorectified colour imagery product. Complements other OS Mastermap\xae Layers. Regularly maintained and updated. Available to order over the internet.',
        'responsible-organisation': [
            {
                'contact-info': {
                    'email': 'customerservices@ordnancesurvey.co.uk'
                },
                'organisation-name': 'Ordnance Survey',
                'role': 'publisher',
                'position-name': 'Customer services',
            }
        ],
        'publisher': 'Ordnance Survey',
        'contact': 'Ordnance Survey',
        'contact-email': 'customerservices@ordnancesurvey.co.uk',
        'frequency-of-update': 'asNeeded',
        'keyword-inspire-theme': ['Land and premises', 'Orthoimagery'],
        'keyword-controlled-other': ['Land and premises', 'Orthoimagery'],
        'keyword-free-text': [],
        'tags': ['Land and premises', 'Orthoimagery'],
        'limitations-on-public-access': [],
        'use-constraints': [],
        'spatial-data-service-type': '',
        'spatial-resolution': '<gco:Distance xmlns:gco="http://www.isotc211.org/2005/gco" xmlns:gts="http://www.isotc211.org/2005/gts" xmlns:gml="http://www.opengis.net/gml/3.2" xmlns:gmx="http://www.isotc211.org/2005/gmx" xmlns:gsr="http://www.isotc211.org/2005/gsr" xmlns:gss="http://www.isotc211.org/2005/gss" xmlns:gmd="http://www.isotc211.org/2005/gmd" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" uom="urn:ogc:def:uom:EPSG::9001">25</gco:Distance>',
        'equivalent-scale': [],
        'dataset-language': [],
        'topic-category': ['imageryBaseMapsEarthCover'],
        'extent-controlled': [],
        'extent-free-text': [],
        'bbox-west-long': '-8.45472',
        'bbox-east-long': '1.78024',
        'bbox-north-lat': '60.8599',
        'bbox-south-lat': '49.8634',
        'temporal-extent-begin': '',
        'temporal-extent-end': '',
        'vertical-extent': '',
        'coupled-resource': [],
        'additional-information-source': '',
        'data-format': [
            {'version': 'not applicable', 'name': 'JPEG'}
        ],
        'resource-locator': [
            {
                'url': 'http://www.ordnancesurvey.co.uk/oswebsite/products/osmastermap/layers/imagery/',
                'function': 'information',
            }
        ],
        'url': 'http://www.ordnancesurvey.co.uk/oswebsite/products/osmastermap/layers/imagery/',
        'conformity-specification': '<gmd:specification xmlns:gmd="http://www.isotc211.org/2005/gmd" xmlns:gts="http://www.isotc211.org/2005/gts" xmlns:gml="http://www.opengis.net/gml/3.2" xmlns:gmx="http://www.isotc211.org/2005/gmx" xmlns:gsr="http://www.isotc211.org/2005/gsr" xmlns:gss="http://www.isotc211.org/2005/gss" xmlns:gco="http://www.isotc211.org/2005/gco" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><gmd:CI_Citation><gmd:title><gco:CharacterString>OS MasterMap Imagery Specification</gco:CharacterString></gmd:title><gmd:date><gmd:CI_Date><gmd:date><gco:Date>2010-08-19</gco:Date></gmd:date><gmd:dateType><gmd:CI_DateTypeCode codeList="http://www.isotc211.org/2005/resources/codeList.xml#CI_DateTypeCode" codeListValue="publication"/></gmd:dateType></gmd:CI_Date></gmd:date><gmd:identifier><gmd:MD_Identifier><gmd:code><gco:CharacterString>http://www.ordnancesurvey.co.uk/oswebsite/products/osmastermap/layers/imagery/technical.html</gco:CharacterString></gmd:code></gmd:MD_Identifier></gmd:identifier></gmd:CI_Citation></gmd:specification>',
        'conformity-pass': 'true',
        'conformity-explanation': 'conforms',
        'lineage': 'Aerial imagery processed by Ordnance Survey',
    }

    def test_crud_document(self):
        self.assert_false(self.document)
        url = self.gemini.url_for(0)
        content = self.gemini.get_content(url)
        self.document = self.create_harvested_document(url=url, content=content)
        self.assert_equal(self.document.url, url)
        self.assert_equal(self.document.content, content)
        dup = HarvestedDocument.get(self.document.id)
        self.delete_commit(self.document)
        self.assert_raises(Exception, HarvestSource.get, self.document.id)

    def test_read_values_example0(self):
        self.assert_read_values(0, self.expect_values0)

    def test_read_values_example1(self):
        self.assert_read_values(1, self.expect_values1)

    def assert_read_values(self, example_index, expect_values):
        url = self.gemini.url_for(example_index)
        content = self.gemini.get_content(url)
        self.document = self.create_harvested_document(url=url, content=content)
        values = self.document.read_values()
        self.assert_gemini_values(values, expect_values)

    def assert_gemini_values(self, values, expect_values):
        for name in expect_values:
            value = values[name]
            expect = expect_values[name]
            self.assert_gemini_value(value, expect, name)

    def assert_gemini_value(self, value, expect, name):
        try:
            self.assert_equal(value, expect)
        except Exception, inst:
            msg = "Attribute '%s' has unexpected value: %s" % (name, inst)
            raise Exception, msg


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

    def url_for(self, index=None):
        if index in [None, 'index.html']:
            name = "index.html"
        else:
            name = self.file_names[index]
        path = os.path.join(self.folder_path(), name)
        if not os.path.exists(path):
            raise Exception, "Gemini example not found on path: %s" % path
        return "file://%s" % path

    # Todo: Refactor url_for() and url_for_bad().
    def url_for_bad(self, index=None):
        if index in [None, 'index.html']:
            name = "index.html"
        else:
            name = self.file_names_bad[index]
        path = os.path.join(self.folder_path_bad(), name)
        if not os.path.exists(path):
            raise Exception, "Gemini bad example not found on path: %s" % path
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

    def get_content(self, url):
        import urllib2
        resource = urllib2.urlopen(url)
        return decode_response(resource)

