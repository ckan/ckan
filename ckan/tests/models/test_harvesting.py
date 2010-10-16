import os
from ckan.tests import *
from ckan.model.harvesting import HarvestSource
from ckan.model.harvesting import HarvestingJob
from ckan.model.harvesting import HarvestedDocument
import ckan.model as model


class GeminiExamples(object):
    """Encapsulates the Gemini example files in ckan/tests/gemini2_examples."""

    gemini_examples = [
        u'00a743bf-cca4-4c19-a8e5-e64f7edbcadd_gemini2.xml',
        u'My series sample.xml',
    ]

    def gemini_examples_path(self):
        from pylons import config
        here_path = config['here']
        examples_path = os.path.join(here_path, 'ckan', 'tests', 'gemini2_examples')
        return examples_path

    def gemini_url(self, index):
        name = self.gemini_examples[index]
        path = os.path.join(self.gemini_examples_path(), name)
        if not os.path.exists(path):
            raise Exception, "Gemini example not found on path: %s" % path
        return "file://%s" % path

    def gemini_content(self, url):
        import urllib2
        resource = urllib2.urlopen(url)
        # Todo: Check the encoding is okay (perhaps change model attribute type)?
        content = resource.read()
        return content


class HarvesterTestCase(GeminiExamples, TestCase):

    require_common_fixtures = False

    def setup(self):
        super(HarvesterTestCase, self).setup()
        self.source = None
        self.job = None
        self.document = None

    def teardown(self):
        if self.document:
            self.delete(self.document)
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
        url = self.gemini_url(0)
        self.source = self.create_harvest_source(url=url)
        self.assert_true(self.source)
        self.assert_true(self.source.id)
        dup = HarvestSource.get(self.source.id)
        self.delete_commit(self.source)
        self.assert_raises(Exception, HarvestSource.get, self.source.id)

    def test_write_package(self):
        url = self.gemini_url(0)
        content = self.gemini_content(url)
        self.document = self.create_harvested_document(url=url, content=content)
        self.source = self.create_harvest_source(url=url)
        count_before = self.count_packages()
        assert self.source.write_package(self.document)
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
            url=self.gemini_url(0)
        )
        self.assert_true(self.source.id)
        self.assert_false(self.job)
        self.job = self.create_harvesting_job(
            source=self.source, 
            user_ref=self.fixture_user_ref
        )

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


class TestHarvestedDocument(HarvesterTestCase):

    def test_crud_document(self):
        self.assert_false(self.document)
        url = self.gemini_url(0)
        content = self.gemini_content(url)
        self.document = self.create_harvested_document(url=url, content=content)
        self.assert_equal(self.document.url, url)
        self.assert_equal(self.document.content, content)
        dup = HarvestedDocument.get(self.document.id)
        self.delete_commit(self.document)
        self.assert_raises(Exception, HarvestSource.get, self.document.id)

    def test_read_attributes(self):
        url = self.gemini_url(0)
        content = self.gemini_content(url)
        self.document = self.create_harvested_document(url=url, content=content)
        data = self.document.read_attributes()
        expect = {
            'guid': '00a743bf-cca4-4c19-a8e5-e64f7edbcadd',
            'metadata-language': 'eng',
            'resource-type': 'dataset',
            # Todo: Sort out how to deal with the different parts.
            'metadata-point-of-contact': ['<gmd:CI_ResponsibleParty xmlns:gmd="http://www.isotc211.org/2005/gmd" xmlns:gco="http://www.isotc211.org/2005/gco" xmlns:gml="http://www.opengis.net/gml/3.2" xmlns:xlink="http://www.w3.org/1999/xlink"><gmd:organisationName><gco:CharacterString>Barrow Borough Council</gco:CharacterString></gmd:organisationName><gmd:contactInfo><gmd:CI_Contact><gmd:address><gmd:CI_Address><gmd:electronicMailAddress><gco:CharacterString>gis@barrowbc.gov.uk</gco:CharacterString></gmd:electronicMailAddress></gmd:CI_Address></gmd:address></gmd:CI_Contact></gmd:contactInfo><gmd:role><gmd:CI_RoleCode codeList="http://standards.iso.org/ittf/PubliclyAvailableStandards/ISO_19139_Schemas/resources/Codelist/gmxCodelists.xml#CI_RoleCode" codeListValue="pointOfContact">pointOfContact</gmd:CI_RoleCode></gmd:role></gmd:CI_ResponsibleParty>'],
            'metadata-date': '2009-10-16',
            'spatial-reference-system': '<gmd:MD_ReferenceSystem xmlns:gmd="http://www.isotc211.org/2005/gmd" xmlns:gco="http://www.isotc211.org/2005/gco" xmlns:gml="http://www.opengis.net/gml/3.2" xmlns:xlink="http://www.w3.org/1999/xlink"><gmd:referenceSystemIdentifier><gmd:RS_Identifier><gmd:code><gco:CharacterString>urn:ogc:def:crs:EPSG::27700</gco:CharacterString></gmd:code></gmd:RS_Identifier></gmd:referenceSystemIdentifier></gmd:MD_ReferenceSystem>',
            'title': 'Council Owned Litter Bins',
            'alternative-title': [],
            # Todo: Sort out how to deal with the different types.
            'dataset-reference-date': ['<gmd:CI_Date xmlns:gmd="http://www.isotc211.org/2005/gmd" xmlns:gco="http://www.isotc211.org/2005/gco" xmlns:gml="http://www.opengis.net/gml/3.2" xmlns:xlink="http://www.w3.org/1999/xlink"><gmd:date><gco:Date>2008-10-10</gco:Date></gmd:date><gmd:dateType><gmd:CI_DateTypeCode codeList="http://standards.iso.org/ittf/PubliclyAvailableStandards/ISO_19139_Schemas/resources/Codelist/gmxCodelists.xml#CI_DateTypeCode" codeListValue="creation">creation</gmd:CI_DateTypeCode></gmd:dateType></gmd:CI_Date>', '<gmd:CI_Date xmlns:gmd="http://www.isotc211.org/2005/gmd" xmlns:gco="http://www.isotc211.org/2005/gco" xmlns:gml="http://www.opengis.net/gml/3.2" xmlns:xlink="http://www.w3.org/1999/xlink"><gmd:date><gco:Date>2009-10-08</gco:Date></gmd:date><gmd:dateType><gmd:CI_DateTypeCode codeList="http://standards.iso.org/ittf/PubliclyAvailableStandards/ISO_19139_Schemas/resources/Codelist/gmxCodelists.xml#CI_DateTypeCode" codeListValue="revision">revision</gmd:CI_DateTypeCode></gmd:dateType></gmd:CI_Date>'],
            'unique-resource-identifier': '<gmd:RS_Identifier xmlns:gmd="http://www.isotc211.org/2005/gmd" xmlns:gco="http://www.isotc211.org/2005/gco" xmlns:gml="http://www.opengis.net/gml/3.2" xmlns:xlink="http://www.w3.org/1999/xlink"><gmd:code><gco:CharacterString>BBC:000006</gco:CharacterString></gmd:code><gmd:codeSpace><gco:CharacterString>Barrow Borough Council</gco:CharacterString></gmd:codeSpace></gmd:RS_Identifier>',
            'abstract': 'Location of Council owned litter bins within Borough.',
            'responsible-organisation': ['<gmd:CI_ResponsibleParty xmlns:gmd="http://www.isotc211.org/2005/gmd" xmlns:gco="http://www.isotc211.org/2005/gco" xmlns:gml="http://www.opengis.net/gml/3.2" xmlns:xlink="http://www.w3.org/1999/xlink"><gmd:organisationName><gco:CharacterString>Barrow Borough Council</gco:CharacterString></gmd:organisationName><gmd:contactInfo><gmd:CI_Contact><gmd:address><gmd:CI_Address><gmd:electronicMailAddress><gco:CharacterString>gis@barrowbc.gov.uk</gco:CharacterString></gmd:electronicMailAddress></gmd:CI_Address></gmd:address></gmd:CI_Contact></gmd:contactInfo><gmd:role><gmd:CI_RoleCode codeList="http://standards.iso.org/ittf/PubliclyAvailableStandards/ISO_19139_Schemas/resources/Codelist/gmxCodelists.xml#CI_RoleCode" codeListValue="pointOfContact">pointOfContact</gmd:CI_RoleCode></gmd:role></gmd:CI_ResponsibleParty>'],
            'frequency-of-update': 'unknown',
            'keyword-inspire-theme': [],
            'keyword-controlled-other': ['Utility and governmental services'],
            'keyword-free-text': [],
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
            # Todo: Sort out how to deal with the different parts.
            'temporal-extent-begin': '1977-03-10T11:45:30',
            'temporal-extent-end': '2005-01-15T09:10:00',
            # Todo: Sort out how to deal with the different parts.
            'vertical-extent': '',
            'coupled-resource': [],
            'additional-information-source': '',
            # Todo: Sort out how to deal with the different parts.
            'data-format': ['<gmd:MD_Format xmlns:gmd="http://www.isotc211.org/2005/gmd" xmlns:gco="http://www.isotc211.org/2005/gco" xmlns:gml="http://www.opengis.net/gml/3.2" xmlns:xlink="http://www.w3.org/1999/xlink"><gmd:name gco:nilReason="inapplicable"/><gmd:version gco:nilReason="inapplicable"/></gmd:MD_Format>'],
            # Todo: Sort out how to deal with the different types.
            'resource-locator': ['http://www.barrowbc.gov.uk'],
            'conformity-specification': '',
            'conformity-pass': '',
            'conformity-explanation': '',
            'lineage': 'Dataset created from ground surveys using Ordnance Survey Mastemap as base.',
        }
        for name in expect:
            self.assert_gemini_value(data[name], expect[name], name)

    def assert_gemini_value(self, data, expect, name):
        try:
            self.assert_equal(data, expect)
        except Exception, inst:
            msg = "Attribute '%s' has unexpected value: %s" % (name, inst)
            raise Exception, msg


