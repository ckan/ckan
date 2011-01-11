from ckan.tests import CheckMethods
from ckan.tests import SkipTest
from pylons import config

from ckan.lib.cswclient import CswError
from ckan.lib.cswclient import CswGetCapabilities
from ckan.lib.cswclient import CswGetRecords
from ckan.lib.cswclient import CswGetRecordById
from ckan.lib.cswclient import CswClient
from ckan.lib.cswclient import GeoNetworkClient
from mock_cswclient import MockGeoNetworkClient

import socket
socket.setdefaulttimeout(1)

class CswRequestTestCase(CheckMethods):

    request_class = None
    request_params = {}
    expect_xml = ""

    def setup(self):
        self.request = self.make_request()

    def teardown(self):
        self.request = None

    def make_request(self):
        if not self.request_class:
            msg = "Test case '%s' has no request_class." % self.__class__
            raise Exception, msg
        return self.request_class(**self.request_params)

    def test_msg(self):
        request_xml = self.request.get_xml()
        self.assert_equal(request_xml, self.expect_xml)


class TestCswGetCapabilities(CswRequestTestCase):

    request_class = CswGetCapabilities
    request_params = {}
    expect_xml = """<?xml version="1.0"?>
<csw:GetCapabilities xmlns:csw="http://www.opengis.net/cat/csw/2.0.2" service="CSW">
    <ows:AcceptVersions xmlns:ows="http://www.opengis.net/ows">
        <ows:Version>2.0.2</ows:Version>
    </ows:AcceptVersions>
    <ows:AcceptFormats xmlns:ows="http://www.opengis.net/ows">
        <ows:OutputFormat>application/xml</ows:OutputFormat>
    </ows:AcceptFormats>
</csw:GetCapabilities>"""


class TestCswGetRecords(CswRequestTestCase):

    request_class = CswGetRecords
    request_params = {"result_type": "results"}
    expect_xml = """<?xml version="1.0"?>
<csw:GetRecords xmlns:csw="http://www.opengis.net/cat/csw/2.0.2"
    xmlns:gmd="http://www.isotc211.org/2005/gmd" service="CSW" version="2.0.2" resultType="results">
    <csw:Query typeNames="gmd:MD_Metadata">
        <csw:ElementName>dc:identifier</csw:ElementName>
        <csw:Constraint version="1.1.0">
            <Filter xmlns="http://www.opengis.net/ogc" xmlns:gml="http://www.opengis.net/gml"/>
        </csw:Constraint>
    </csw:Query>
</csw:GetRecords>"""


class TestCswGetRecordById(CswRequestTestCase):

    request_class = CswGetRecordById
    request_params = {"identifier": "000000000000000000000000000000000000000"}
    expect_xml = """<?xml version="1.0"?>
<csw:GetRecordById xmlns:csw="http://www.opengis.net/cat/csw/2.0.2" service="CSW" version="2.0.2"
    outputSchema="csw:IsoRecord">
    <csw:Id>000000000000000000000000000000000000000</csw:Id>
</csw:GetRecordById>"""


class CswClientTestCase(CheckMethods):

    csw_client_class = CswClient
    base_url = ""
    username = ""
    password = ""
    max_records = 10
    expected_id = '8dc2dddd-e483-4c1a-9482-eb05e8e4314d'

    def setup(self):
        self.client = None
        self.client = self.create_csw_client()
        if self.username and self.password:
            self.client.login()

    def teardown(self):
        if self.username and self.password:
            if hasattr(self, 'client') and self.client:
                self.client.logout()
        self.client = None

    def create_csw_client(self):
        return self.csw_client_class(
            base_url=self.base_url,
            username=self.username,
            password=self.password,
        )

    def test_send_get_capabilities(self):
        xml = self.client.send_get_capabilities()
        self.assert_contains(xml, "csw:Capabilities")

    def test_assert_capabilities(self):
        self.client.assert_capabilities()

    def test_send_get_records(self):
        xml = self.client.send_get_records()
        self.assert_contains(xml, "GetRecordsResponse")

    def test_send_get_record_by_id(self):
        xml = self.client.send_get_record_by_id("8dc2dddd-e483-4c1a-9482-eb05e8e4314d")
        self.assert_contains(xml, "GetRecordByIdResponse")

    def test_get_record_by_id(self):
        xml = self.client.get_record_by_id("8dc2dddd-e483-4c1a-9482-eb05e8e4314d")
        self.assert_contains(xml, "gmd:MD_Metadata")

    def test_get_identifiers(self):
        ids = self.client.get_identifiers()
        self.assert_contains(ids, self.expected_id)

    def test_get_records(self):
        records = self.client.get_records(max_records=self.max_records)
        self.assert_true(len(records))

    def test_extract_identifiers(self):
        get_records_response = """<?xml version="1.0" encoding="UTF-8"?>
<csw:GetRecordsResponse xmlns:csw="http://www.opengis.net/cat/csw/2.0.2" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.opengis.net/cat/csw/2.0.2 http://schemas.opengis.net/csw/2.0.2/CSW-discovery.xsd">
  <csw:SearchStatus timestamp="2010-10-21T23:38:53" />
  <csw:SearchResults numberOfRecordsMatched="3" numberOfRecordsReturned="3" elementSet="full" nextRecord="0">
    <csw:Record xmlns:geonet="http://www.fao.org/geonetwork" xmlns:ows="http://www.opengis.net/ows" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dct="http://purl.org/dc/terms/">
      <dc:identifier>521ca63d-dad9-43fe-aebe-1138ffee530f</dc:identifier>
    </csw:Record>
    <csw:Record xmlns:geonet="http://www.fao.org/geonetwork" xmlns:ows="http://www.opengis.net/ows" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dct="http://purl.org/dc/terms/">
      <dc:identifier>8dc2dddd-e483-4c1a-9482-eb05e8e4314d</dc:identifier>
    </csw:Record>
    <csw:Record xmlns:geonet="http://www.fao.org/geonetwork" xmlns:ows="http://www.opengis.net/ows" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dct="http://purl.org/dc/terms/">
      <dc:identifier>8d2aaadd-6ad8-41e0-9cd3-ef743ba19887</dc:identifier>
    </csw:Record>
  </csw:SearchResults>
</csw:GetRecordsResponse>"""
        ids = self.client.extract_identifiers(get_records_response)
        self.assert_isinstance(ids, list)
        self.assert_len(ids, 3)
        self.assert_contains(ids, "521ca63d-dad9-43fe-aebe-1138ffee530f")
        self.assert_contains(ids, "8dc2dddd-e483-4c1a-9482-eb05e8e4314d")
        self.assert_contains(ids, "8d2aaadd-6ad8-41e0-9cd3-ef743ba19887")


class BlankTests(CswClientTestCase):

    def test_send_get_capabilities(self): pass

    def test_assert_capabilities(self): pass

    def test_send_get_records(self): pass

    def test_send_get_record_by_id(self): pass

    def test_get_record_by_id(self): pass

    def test_get_identifiers(self): pass

    def test_get_records(self): pass

    def test_extract_identifiers(self): pass



class GeoNetworkClientTestCase(CswClientTestCase):

    csw_client_class = GeoNetworkClient


class TestGeoNetworkClient(GeoNetworkClientTestCase):

    csw_client_class = MockGeoNetworkClient


class TestGeoNetworkClientSite(GeoNetworkClientTestCase):

    # Test with real example GeoNetwork site.
    base_url=config.get('example_csw_url', '')
    username=config.get('example_csw_username', '')
    password=config.get('example_csw_password', '')

    def setup(self):
        if not self.base_url:
            raise SkipTest
        super(TestGeoNetworkClientSite, self).setup()


class TestGeoNetworkClientSiteNoAuth(TestGeoNetworkClientSite):

    # Test with real example GeoNetwork site.
    username = ''
    password = ''
    expected_id = '8d2aaadd-6ad8-41e0-9cd3-ef743ba19887'


class TestGeoNetworkClientSiteBadAuth(BlankTests, TestGeoNetworkClientSite):

    username = 'mickey'
    password = 'mouse'
    expected_id = '8d2aaadd-6ad8-41e0-9cd3-ef743ba19887'

    # Since there is a bad username and password, setup will fail.
    def setup(self):
        super_method = super(TestGeoNetworkClientSiteBadAuth, self).setup
        self.assert_raises(CswError, super_method)


class TestGeoNetworkClientSiteDown(BlankTests, GeoNetworkClientTestCase):

    base_url = 'http://128.0.0.1:44444'
    username = 'a'
    password = 'b'

    # Since there is a username and password, setup and teardown will fail.
    def setup(self):
        super_method = super(TestGeoNetworkClientSiteDown, self).setup
        self.assert_raises(CswError, super_method)

    def teardown(self):
        super_method = super(TestGeoNetworkClientSiteDown, self).teardown
        self.assert_raises(CswError, super_method)


class TestGeoNetworkClientSiteDownNoAuth(BlankTests, GeoNetworkClientTestCase):

    base_url = 'http://128.0.0.1:44444'
    username = ''
    password = ''

    # Since there is no username and password, setup and teardown won't error.

    # However, the send methods won't work....
    def test_send_get_record_by_id(self):
        super_method = GeoNetworkClientTestCase.test_send_get_record_by_id
        self.assert_raises(CswError, super_method, self)

