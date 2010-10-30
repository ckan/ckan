#!/usr/bin/env python
import urllib
import urllib2
import cookielib
from lxml import etree

class CswError(Exception): pass

class CswRequest(object):

    template = ""

    def __init__(self, **kwds):
        self.params = kwds

    def get_params(self):
        return self.params

    def get_xml(self):
        if self.template == None:
            raise CswError, "No template attribute on class %s." % self.__class__
        return self.template % self.get_params()


class CswGetCapabilities(CswRequest):

    template = """<?xml version="1.0"?>
<csw:GetCapabilities xmlns:csw="http://www.opengis.net/cat/csw/2.0.2" service="CSW">
    <ows:AcceptVersions xmlns:ows="http://www.opengis.net/ows">
        <ows:Version>2.0.2</ows:Version>
    </ows:AcceptVersions>
    <ows:AcceptFormats xmlns:ows="http://www.opengis.net/ows">
        <ows:OutputFormat>application/xml</ows:OutputFormat>
    </ows:AcceptFormats>
</csw:GetCapabilities>"""


class CswGetRecords(CswRequest):

    template = """<?xml version="1.0"?>
<csw:GetRecords xmlns:csw="http://www.opengis.net/cat/csw/2.0.2"
    xmlns:gmd="http://www.isotc211.org/2005/gmd" service="CSW" version="2.0.2" resultType="%(result_type)s">
    <csw:Query typeNames="gmd:MD_Metadata">
        <csw:ElementName>dc:identifier</csw:ElementName>
        <csw:Constraint version="1.1.0">
            <Filter xmlns="http://www.opengis.net/ogc" xmlns:gml="http://www.opengis.net/gml"/>
        </csw:Constraint>
    </csw:Query>
</csw:GetRecords>"""

    def __init__(self, result_type='results'):
        super(CswGetRecords, self).__init__(result_type=result_type)


class CswGetRecordById(CswRequest):

    template = """<?xml version="1.0"?>
<csw:GetRecordById xmlns:csw="http://www.opengis.net/cat/csw/2.0.2" service="CSW" version="2.0.2"
    outputSchema="csw:IsoRecord">
    <csw:Id>%(identifier)s</csw:Id>
</csw:GetRecordById>"""

    def __init__(self, identifier):
        super(CswGetRecordById, self).__init__(identifier=identifier)


class CswClient(object):

    namespaces = {
        "csw": "http://www.opengis.net/cat/csw/2.0.2",
        "xsi": "http://www.w3.org/2001/XMLSchema-instance",
        "geonet": "http://www.fao.org/geonetwork",
        "dc": "http://purl.org/dc/elements/1.1/",
        "dct": "http://purl.org/dc/terms/",
        "gmd": "http://www.isotc211.org/2005/gmd",
    }

    def __init__(self, base_url, csw_uri='', login_uri='', logout_uri='', username=None, password=None):
        self.base_url = base_url
        self.csw_uri = csw_uri
        self.login_uri = login_uri
        self.logout_uri = logout_uri
        self.username = username
        self.password = password
        self.login_url = self.base_url + self.login_uri
        self.logout_url = self.base_url + self.logout_uri
        self.csw_url = self.base_url + self.csw_uri
        self.opener = None

    def assert_capabilities(self):
        xml = self.send_get_capabilities()
        # Check document type is csw:Capabilities.
        if "<csw:Capabilities" not in xml:
            msg = "Doesn't look like a capabilities response: %s" % xml
            raise CswError, msg
        # Check service type is CSW.
        if "<ows:ServiceType>CSW</ows:ServiceType>" not in xml:
            msg = "Doesn't look like a CSW service: %s" % xml
            raise CswError, msg
        # Check is capable of GetRecords operation.
        if "<ows:Operation name=\"GetRecords\">" not in xml:
            msg = "Doesn't look like GetRecords operation is supported: %s" % xml
            raise CswError, msg
        # Check is capable of GetRecordById operation.
        if "<ows:Operation name=\"GetRecordById\">" not in xml:
            msg = "Doesn't look like GetRecordById operation is supported: %s" % xml
            raise CswError, msg
        # Todo: Change above code to use XPaths?

    def get_records(self, max_records=None):
        records = []
        for id in self.get_identifiers():
            record = self.get_record_by_id(id)
            records.append(record)
            if max_records and len(records) == max_records:
                break
        return records

    def get_identifiers(self):
        response = self.send_get_records()
        return self.extract_identifiers(response)
       
    def get_record_by_id(self, identifier):
        response = self.send_get_record_by_id(identifier)
        return self.extract_metadata(response)

    def send_get_capabilities(self):
        return self.send(CswGetCapabilities())

    def send_get_records(self):
        return self.send(CswGetRecords())
       
    def send_get_record_by_id(self, identifier): 
        return self.send(CswGetRecordById(identifier=identifier))

    def send(self, csw_request):
        csw_request_xml = self.get_xml_from_csw_request(csw_request)
        http_header = {"Content-type": "application/xml", "Accept": "text/plain"}
        http_request = urllib2.Request(self.csw_url, csw_request_xml, http_header)
        try:
            http_response = self.urlopen(http_request)
        except Exception, inst:
            msg = "Couldn't send CSW request to CSW server: %s: %s: %s" % (
                self.base_url, inst, csw_request_xml
            )
            raise CswError, msg 
        csw_response_xml = http_response.read()
        return csw_response_xml

    def get_xml_from_csw_request(self, csw_request):
        if isinstance(csw_request, CswRequest):
            csw_request_xml = csw_request.get_xml()
        else:
            csw_request_xml = csw_request
        return csw_request_xml

    def extract_identifiers(self, get_records_response):
        parser = etree.XMLParser(remove_blank_text=True)
        tree = etree.fromstring(get_records_response, parser=parser)
        xpath = '//csw:Record/dc:identifier/text()'
        return tree.xpath(xpath, namespaces=self.namespaces)

    def extract_metadata(self, get_record_by_id_response):
        parser = etree.XMLParser(remove_blank_text=True)
        tree = etree.fromstring(get_record_by_id_response, parser=parser)
        xpath = 'gmd:MD_Metadata'
        elems = tree.xpath(xpath, namespaces=self.namespaces)
        if isinstance(elems, list) and len(elems) == 1:
            elem = elems[0]
        else:
            msg = "Unexpected return value from etree.xpath: %s" % repr(elems)
            raise CswError, msg
        return etree.tostring(elem)

    def login(self):
        if not (self.username and self.password):
            return
        self.logout()
        http_params = urllib.urlencode({"username": self.username, "password": self.password})
        http_header = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}
        http_request = urllib2.Request(self.login_url, http_params, http_header)
        try:
            http_response = self.urlopen(http_request)
        except Exception, inst:
            msg = "Couldn't login to CSW with given credentials: %s" % inst
            raise CswError, msg 
        cookie_jar = cookielib.CookieJar()
        cookie_jar.extract_cookies(http_response, http_request)
        cookie_handler= urllib2.HTTPCookieProcessor(cookie_jar)
        redirect_handler= urllib2.HTTPRedirectHandler()
        self.opener = urllib2.build_opener(redirect_handler, cookie_handler)
        
    def logout(self):
        if not (self.username and self.password):
            return
        http_request = urllib2.Request(self.logout_url)
        try:
            http_response = self.urlopen(http_request)
        except Exception, inst:
            msg = "Couldn't logout from CSW server %s: %s" % (
                self.base_url, inst)
            raise CswError, msg 
        xml_response = http_response.read()
        if "<ok />" not in xml_response:
            msg = "Couldn't logout from CSW server %s: %s" % (
                self.base_url, xml_response)
            raise CswError, msg

    def urlopen(self, http_request):
        try:
            if self.opener:
                http_response = self.opener.open(http_request)
            else:
                http_response = urllib2.urlopen(http_request)
        except urllib2.URLError, inst:
            msg = 'Error making CSW server request: %s' % inst
            raise CswError, msg
        else:
            return http_response


class GeoNetworkClient(CswClient):

    def __init__(self, base_url, username='', password=''):
        login_uri = '/../xml.user.login'
        logout_uri = '/../xml.user.logout'
        super(GeoNetworkClient, self).__init__(
            base_url=base_url,
            login_uri=login_uri,
            logout_uri=logout_uri,
            username=username,
            password=password,
        )

