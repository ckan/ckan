import logging
import datetime
from meta import *
from lxml import etree
import urllib2

from types import make_uuid
from types import JsonType
from core import *
from domain_object import DomainObject
from package import Package
from ckan.lib.cswclient import CswClient
from ckan.lib.cswclient import CswError

log = logging.getLogger(__name__)

__all__ = [
    'HarvestSource', 'harvest_source_table',
    'HarvestingJob', 'harvesting_job_table',
    'HarvestedDocument', 'harvested_document_table',
]

def decode_response(resp):
    """Decode a response to unicode
    """
    encoding = resp.headers['content-type'].split('charset=')[-1]
    content = resp.read()
    try:
        data = unicode(content, encoding)
    except LookupError:
        data = unicode(content, 'utf8') # XXX is this a fair assumption?
    return data

class HarvesterError(Exception): pass

class HarvesterUrlError(HarvesterError): pass

class DomainObject(DomainObject):

    key_attr = 'id'

    @classmethod 
    def get(self, key, default=Exception, attr=None):
        """Finds a single entity in the register."""
        if attr == None:
            attr = self.key_attr
        kwds = {attr: key}
        o = self.filter(**kwds).first()
        if o:
            return o
        if default != Exception:
            return default
        else:
            raise Exception, "%s not found: %s" % (self.__name__, key)

    @classmethod 
    def filter(self, **kwds): 
        query = Session.query(self).autoflush(False)
        return query.filter_by(**kwds)

    @classmethod 
    def create_save(self, **kwds):
        # Create an object instance.
        object = self.create(**kwds)
        # Create a record for the object instance.
        object.save()
        # Return the object instance.
        return object

    @classmethod 
    def create(self, **kwds):
        # Initialise object key attribute.
        if self.key_attr not in kwds:
            kwds[self.key_attr] = self.create_key()
        # Create an object instance.
        return self(**kwds)

    @classmethod 
    def create_key(self, **kwds):
        # By default, it's a new UUID.
        return make_uuid()


class HarvestSource(DomainObject):

    def write_package(self, content):
        from ckan.lib.base import _
        import ckan.forms
        import ckan.model as model
        package = None
        # Look for document with matching Gemini GUID.
        gemini_document = GeminiDocument(content)
        gemini_values = gemini_document.read_values()
        gemini_guid = gemini_values['guid']
        harvested_documents = HarvestedDocument.filter(guid=gemini_guid).all()
        if len(harvested_documents) > 1:
            # A programming error.
            raise Exception, "More than one harvested document GUID %s in database." % gemini_guid
        elif len(harvested_documents) == 1:
            harvested_document = harvested_documents[0]
            if harvested_document.source.id != self.id:
                # A 'user' error.
                raise HarvesterError, "Another source is using metadata GUID %s." % self.id
            package = harvested_document.package
        else:
            harvested_document = None
            package = None
        package_data = {
            'name': gemini_values['guid'],
            'title': gemini_values['title'],
            'extras': gemini_values,
        }
        if package == None:
            # Create package from data.
            try:
                user_editable_groups = []
                fs = ckan.forms.get_standard_fieldset(user_editable_groups=user_editable_groups)
                try:
                    fa_dict = ckan.forms.edit_package_dict(ckan.forms.get_package_dict(fs=fs, user_editable_groups=user_editable_groups), package_data)
                except ckan.forms.PackageDictFormatError, exception:
                    msg = 'Package format incorrect: %r' % exception
                    raise Exception, msg
                else:
                    fs = fs.bind(model.Package, data=fa_dict, session=model.Session)
                    # Validate the fieldset.
                    is_valid = fs.validate()
                    if is_valid:
                        # Construct new revision.
                        rev = model.repo.new_revision()
                        #rev.author = self.rest_api_user
                        rev.message = _(u'Harvester: Created package %s') % str(fs.model.id)
                        # Construct catalogue entity.
                        fs.sync()
                        # Construct access control entities.
                        #if self.rest_api_user:
                        #    admins = [model.User.by_name(self.rest_api_user.decode('utf8'))]
                        #else:
                        #    admins = []
                        # Todo: Better 'admins' than this?
                        admins = []
                        model.setup_default_user_roles(fs.model, admins)
                        # Commit
                        model.repo.commit()        
                        package = fs.model
                    else:
                        # Complain about validation errors.
                        msg = 'Validation error:'
                        errors = fs.errors.items()
                        for error in errors:
                            attr_name = error[0].name
                            error_msg = error[1][0]
                            msg += ' %s: %s' % (attr_name.capitalize(), error_msg)
                        raise HarvesterError, msg
            except:
                model.Session.rollback()
                model.Session.close()
                raise
            if harvested_document == None:
                harvested_document = self.create_document(content=content, guid=gemini_guid, package=package)
            else:
                harvested_document.content = content
                harvested_document.save()
            return package
        else:
            if gemini_values == harvested_document.read_values():
                return None
            else:
                from ckan.forms import GetPackageFieldset
                fieldset = GetPackageFieldset().fieldset
                from ckan.forms import GetEditFieldsetPackageData
                fieldset_data = GetEditFieldsetPackageData(
                    fieldset=fieldset, package=package, data=package_data).data
                bound_fieldset = fieldset.bind(package, data=fieldset_data)
                log_message = u'harvester'
                author = u''
                from ckan.lib.package_saver import WritePackageFromBoundFieldset
                from ckan.lib.package_saver import ValidationException
                try:
                    WritePackageFromBoundFieldset(
                        fieldset=bound_fieldset,
                        log_message=log_message,
                        author=author,
                    )
                except ValidationException:
                    msgs = []
                    for (field, errors) in bound_fieldset.errors.items():
                        for error in errors:
                            msg = "%s: %s" % (field.name, error)
                            msgs.append(msg)
                    msg = "Fieldset validation errors: %s" % msgs
                    raise HarvesterError, msg
                else:
                    return package

    def create_document(self, content, guid, package):
        document = HarvestedDocument.create_save(content=content, guid=guid, package=package)
        self.documents.append(document)
        self.save()
        return document


class HarvestingJob(DomainObject):

    def harvest_documents(self):
        self.get_report()
        self.set_status_running()
        self.save()
        try:
            try:
                content = self.get_source_content()
            except HarvesterUrlError, exception:
                msg = "Error harvesting source: %s" % exception
                self.report_error(msg)
            else:
                source_type = self.detect_source_type(content)
                if source_type == None:
                    self.report_error("Unable to detect source type from content.")
                elif source_type == 'doc':
                    self.harvest_document(content=content)
                elif source_type == 'csw':
                    self.harvest_csw_documents(url=self.source.url)
                elif source_type == 'waf':
                    self.harvest_waf_documents(content=content)
                else:
                    raise Exception, "Source type '%s' not supported." % source_type
        except Exception, inst:
            self.set_status_error()
            self.report_error("Harvesting system error.")
            self.save()
            self.save_report()
            raise
        else:
            if self.report_has_errors():
                self.set_status_error()
            else:
                self.set_status_success()
            self.save()
            self.save_report()

    def report_error(self, msg):
        self.get_report()['errors'].append(msg)
        self.errors += msg

    def report_package(self, msg):
        self.get_report()['packages'].append(msg)

    def get_report(self):
        if not hasattr(self, '_report'):
            self._report = {
                'packages': [],
                'errors': [],
            }
        return self._report

    def save_report(self):
        self.report = self.get_report()
        self.save()

    def report_has_errors(self):
        return bool(self.get_report()['errors'])

    def get_source_content(self):
        return self.get_content(self.source.url)

    def get_content(self, url):
        try:
            http_response = urllib2.urlopen(url)
            return decode_response(http_response)
        except Exception, inst:
            msg = "Unable to get content for URL: %s: %r" % (url, inst)
            raise HarvesterUrlError(msg)

    def detect_source_type(self, content):
        if "<gmd:MD_Metadata" in content:
            return 'doc'
        if "<ows:ExceptionReport" in content:
            return 'csw'
        if "<html" in content:
            return 'waf'

    def harvest_document(self, content):
        try:
            self.validate_document(content)
        except Exception, exception:
            msg = "Error validating harvested content: %s" % exception
            self.report_error(msg)
        else:
            try:
                package = self.source.write_package(content)
            except HarvesterError, exception:
                msg = "%s" % exception
                self.report_error(msg)
            except Exception, exception:
                msg = "System error writing package from harvested content: %s" % exception
                self.report_error(msg)
                # Todo: Print traceback to exception log?
                raise
            else:
                if package:
                    self.report_package(package.id)

    def harvest_csw_documents(self, url):
        try:
            csw_client = CswClient(base_url=url)
            records = csw_client.get_records()
        except CswError, error:
            msg = "Couldn't get records from CSW: %s: %s" % (url, error)
            self.report_error(msg)

        for content in records:
            self.harvest_document(content=content)

    def harvest_waf_documents(self, content):
        for url in self.extract_urls(content):
            try:
                content = self.get_content(url)
            except HarvesterError, error:
                msg = "Couldn't harvest WAF link: %s: %s" % (url, error)
                self.report_error(msg)
            else:
                if "<gmd:MD_Metadata" in content:
                    self.harvest_document(content=content)
        if not self.get_report()['packages']:
            self.report_error("Couldn't find any links to metadata files.")

    def extract_urls(self, content):
        try:
            parser = etree.HTMLParser()
            tree = etree.fromstring(content, parser=parser)
        except Exception, inst:
            msg = "Couldn't parse content into a tree: %s: %s" % (inst, content)
            raise HarvesterError, msg
        urls = []
        for url in tree.xpath('//a/@href'):
            url = url.strip()
            if not url:
                continue
            if '?' in url:
                continue
            if '/' in url:
                continue
            urls.append(url)
        base_url = self.source.url
        base_url = base_url.split('/')
        if 'index' in base_url[-1]:
            base_url.pop()
        base_url = '/'.join(base_url)
        base_url.rstrip('/')
        base_url += '/'
        return [base_url + i for i in urls]

    def validate_document(self, content):
        pass

    def set_status_success(self):
        self.set_status(u"Success")

    def set_status_running(self):
        self.set_status(u"Running")

    def set_status_error(self):
        self.set_status(u"Error")

    def set_status(self, status):
        self.status = status


class MappedXmlObject(object):

    elements = []


class MappedXmlDocument(MappedXmlObject):

    def __init__(self, content):
        self.content = content

    def read_values(self):
        values = {}
        tree = self.get_content_tree()
        for element in self.elements:
            values[element.name] = element.read_value(tree)
        self.infer_values(values)
        return values

    def get_content_tree(self):
        parser = etree.XMLParser(remove_blank_text=True)
        if type(self.content) == unicode:
            content = self.content.encode('utf8')
        else:
            content = self.content
        return etree.fromstring(content, parser=parser)

    def infer_values(self, values):
        pass


class MappedXmlElement(MappedXmlObject):

    namespaces = {}

    def __init__(self, name, search_paths=[], multiplicity="*", elements=[]):
        self.name = name
        self.search_paths = search_paths
        self.multiplicity = multiplicity
        self.elements = elements or self.elements

    def read_value(self, tree):
        values = []
        for xpath in self.get_search_paths():
            elements = self.get_elements(tree, xpath)
            values = self.get_values(elements)
            if values:
                break
        return self.fix_multiplicity(values)

    def get_search_paths(self):
        if type(self.search_paths) != type([]):
            search_paths = [self.search_paths]
        else:
            search_paths = self.search_paths
        return search_paths

    def get_elements(self, tree, xpath):
        return tree.xpath(xpath, namespaces=self.namespaces)

    def get_values(self, elements):
        values = []
        if len(elements) == 0:
            pass
        else:
            for element in elements:
                value = self.get_value(element)
                values.append(value)
        return values

    def get_value(self, element):
        if self.elements:
            value = {}
            for child in self.elements:
                value[child.name] = child.read_value(element)
            return value
        elif type(element) == etree._ElementStringResult:
            value = str(element)
        elif type(element) == etree._ElementUnicodeResult:
            value = unicode(element)
        else:
            value = self.element_tostring(element)
        return value

    def element_tostring(self, element):
        return etree.tostring(element, pretty_print=False)

    def fix_multiplicity(self, values):
        if self.multiplicity == "0":
            if values:
                raise HarvesterError, "Values found for element '%s': %s" % (self.name, values)
            else:
                return ""
        elif self.multiplicity == "1":
            if values:
                return values[0]
            else:
                raise HarvesterError, "Value not found for element '%s'" % self.name
        elif self.multiplicity == "*":
            return values
        elif self.multiplicity == "0..1":
            if values:
                return values[0]
            else:
                return ""
        elif self.multiplicity == "1..*":
            return values
        else:
            raise HarvesterError, "Can't fix element values for multiplicity '%s'." % self.multiplicity


class GeminiElement(MappedXmlElement):

    namespaces = {
       "gts": "http://www.isotc211.org/2005/gts",
       "gml": "http://www.opengis.net/gml/3.2",
       "gmx": "http://www.isotc211.org/2005/gmx",
       "gsr": "http://www.isotc211.org/2005/gsr",
       "gss": "http://www.isotc211.org/2005/gss",
       "gco": "http://www.isotc211.org/2005/gco",
       "gmd": "http://www.isotc211.org/2005/gmd",
       "srv": "http://www.isotc211.org/2005/srv",
       "xlink": "http://www.w3.org/1999/xlink",
       "xsi": "http://www.w3.org/2001/XMLSchema-instance",
    }


class GeminiResponsibleParty(GeminiElement):

    elements = [
        GeminiElement(
            name="organisation-name",
            search_paths=[
                "gmd:organisationName/gco:CharacterString/text()",
            ],
            multiplicity="0..1",
        ),
        GeminiElement(
            name="position-name",
            search_paths=[
                "gmd:positionName/gco:CharacterString/text()",
            ],
            multiplicity="0..1",
        ),
        GeminiElement(
            name="contact-info",
            search_paths=[
                "gmd:contactInfo/gmd:CI_Contact",
            ],
            multiplicity="0..1",
            elements = [
                GeminiElement(
                    name="email",
                    search_paths=[
                        "gmd:address/gmd:CI_Address/gmd:electronicMailAddress/gco:CharacterString/text()",
                    ],
                    multiplicity="0..1",
                ),
            ]
        ),
        GeminiElement(
            name="role",
            search_paths=[
                "gmd:role/gmd:CI_RoleCode/@codeListValue",
            ],
            multiplicity="0..1",
        ),
    ]


class GeminiResourceLocator(GeminiElement):

    elements = [
        GeminiElement(
            name="url",
            search_paths=[
                "gmd:linkage/gmd:URL/text()",
            ],
            multiplicity="1",
        ),
        GeminiElement(
            name="function",
            search_paths=[
                "gmd:function/gmd:CI_OnLineFunctionCode/@codeListValue",
            ],
            multiplicity="0..1",
        ),
    ]


class GeminiDataFormat(GeminiElement):

    elements = [
        GeminiElement(
            name="name",
            search_paths=[
                "gmd:name/gco:CharacterString/text()",
            ],
            multiplicity="0..1",
        ),
        GeminiElement(
            name="version",
            search_paths=[
                "gmd:version/gco:CharacterString/text()",
            ],
            multiplicity="0..1",
        ),
    ]


class GeminiReferenceDate(GeminiElement):

    elements = [
        GeminiElement(
            name="type",
            search_paths=[
                "gmd:dateType/gmd:CI_DateTypeCode/@codeListValue",
                "gmd:dateType/gmd:CI_DateTypeCode/text()",
            ],
            multiplicity="1",
        ),
        GeminiElement(
            name="value",
            search_paths=[
                "gmd:date/gco:Date/text()",
                "gmd:date/gco:DateTime/text()",
            ],
            multiplicity="1",
        ),
    ]


class GeminiDocument(MappedXmlDocument):

    # Attribute specifications from "XPaths for GEMINI" by Peter Parslow.

    elements = [
        GeminiElement(
            name="guid",
            search_paths="gmd:fileIdentifier/gco:CharacterString/text()",
            multiplicity="0..1",
        ),
        GeminiElement(
            name="metadata-language",
            search_paths=[
                "gmd:language/gmd:LanguageCode/@codeListValue",
                "gmd:language/gmd:LanguageCode/text()",
            ],
            multiplicity="1",
        ),
        GeminiElement(
            name="resource-type",
            search_paths=[
                "gmd:hierarchyLevel/gmd:MD_ScopeCode/@codeListValue",
                "gmd:hierarchyLevel/gmd:MD_ScopeCode/text()",
            ],
            multiplicity="1",
        ),
        GeminiResponsibleParty(
            name="metadata-point-of-contact",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:pointOfContact/gmd:CI_ResponsibleParty",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:pointOfContact/gmd:CI_ResponsibleParty",
            ],
            multiplicity="1..*",
        ),
        GeminiElement(
            name="metadata-date",
            search_paths=[
                "gmd:dateStamp/gco:Date/text()",
                "gmd:dateStamp/gco:DateTime/text()",
            ],
            multiplicity="1",
        ),
        GeminiElement(
            name="spatial-reference-system",
            search_paths=[
                "gmd:referenceSystemInfo/gmd:MD_ReferenceSystem",
            ],
            multiplicity="0..1",
        ),
        GeminiElement(
            name="title",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:title/gco:CharacterString/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:citation/gmd:CI_Citation/gmd:title/gco:CharacterString/text()",
            ],
            multiplicity="1",
        ),
        GeminiElement(
            name="alternative-title",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:alternativeTitle/gco:CharacterString/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:citation/gmd:CI_Citation/gmd:alternativeTitle/gco:CharacterString/text()",
            ],
            multiplicity="*",
        ),
        GeminiReferenceDate(
            name="dataset-reference-date",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:date/gmd:CI_Date",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:citation/gmd:CI_Citation/gmd:date/gmd:CI_Date",
            ],
            multiplicity="*",
        ),
        # Todo: Suggestion from PP not to bother pulling this into the package.
        GeminiElement(
            name="unique-resource-identifier",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:identifier/gmd:RS_Identifier",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:citation/gmd:CI_Citation/gmd:identifier/gmd:RS_Identifier",
            ],
            multiplicity="1",
        ),
        GeminiElement(
            name="abstract",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:abstract/gco:CharacterString/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:abstract/gco:CharacterString/text()",
            ],
            multiplicity="1",
        ),
        GeminiResponsibleParty(
            name="responsible-organisation",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:pointOfContact/gmd:CI_ResponsibleParty",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:pointOfContact/gmd:CI_ResponsibleParty",
            ],
            multiplicity="1..*",
        ),
        GeminiElement(
            name="frequency-of-update",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:resourceMaintenance/gmd:MD_MaintenanceInformation/gmd:maintenanceAndUpdateFrequency/gmd:MD_MaintenanceFrequencyCode/@codeListValue",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:resourceMaintenance/gmd:MD_MaintenanceInformation/gmd:maintenanceAndUpdateFrequency/gmd:MD_MaintenanceFrequencyCode/@codeListValue",

                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:resourceMaintenance/gmd:MD_MaintenanceInformation/gmd:maintenanceAndUpdateFrequency/gmd:MD_MaintenanceFrequencyCode/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:resourceMaintenance/gmd:MD_MaintenanceInformation/gmd:maintenanceAndUpdateFrequency/gmd:MD_MaintenanceFrequencyCode/text()",
            ],
            multiplicity="0..1",
        ),
        GeminiElement(
            name="keyword-inspire-theme",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:descriptiveKeywords/gmd:MD_Keywords/gmd:keyword/gco:CharacterString/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:descriptiveKeywords/gmd:MD_Keywords/gmd:keyword/gco:CharacterString/text()",
            ],
            multiplicity="*",
        ),
        GeminiElement(
            name="keyword-controlled-other",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:descriptiveKeywords/gmd:MD_Keywords/gmd:keyword/gco:CharacterString/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:descriptiveKeywords/gmd:MD_Keywords/gmd:keyword/gco:CharacterString/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/srv:keywords/gmd:MD_Keywords/gmd:keyword/gco:CharacterString/text()",
            ],
            multiplicity="*",
        ),
        GeminiElement(
            name="keyword-free-text",
            search_paths=[
            ],
            multiplicity="*",
        ),
        GeminiElement(
            name="limitations-on-public-access",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:resourceConstraints/gmd:MD_LegalConstraints/gmd:accessConstraints/gmd:otherConstraints/gco:CharacterString/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:resourceConstraints/gmd:MD_LegalConstraints/gmd:accessConstraints/gmd:otherConstraints/gco:CharacterString/text()",
            ],
            multiplicity="1..*",
        ),
        GeminiElement(
            name="use-constraints",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:resourceConstraints/gmd:MD_Constraints/gmd:useLimitation/gco:CharacterString/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:resourceConstraints/gmd:MD_Constraints/gmd:useLimitation/gco:CharacterString/text()",
            ],
            multiplicity="*",
        ),
        GeminiElement(
            name="spatial-data-service-type",
            search_paths=[
                "gmd:identificationInfo/srv:SV_ServiceIdentification/srv:serviceType/gco:LocalName",
            ],
            multiplicity="0..1",
        ),
        GeminiElement(
            name="spatial-resolution",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:spatialResolution/gmd:MD_Resolution/gmd:distance/gco:Distance",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:spatialResolution/gmd:MD_Resolution/gmd:distance/gco:Distance",
            ],
            multiplicity="0..1",
        ),
        GeminiElement(
            name="spatial-resolution-units",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:spatialResolution/gmd:MD_Resolution/gmd:distance/gco:Distance/@uom",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:spatialResolution/gmd:MD_Resolution/gmd:distance/gco:Distance/@uom",
            ],
            multiplicity="0..1",
        ),
        GeminiElement(
            name="equivalent-scale",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:spatialResolution/gmd:MD_Resolution/gmd:equivalentScale/gmd:MD_RepresentativeFraction/gmd:denominator/gco:Integer/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:spatialResolution/gmd:MD_Resolution/gmd:equivalentScale/gmd:MD_RepresentativeFraction/gmd:denominator/gco:Integer/text()",
            ],
            multiplicity="*",
        ),
        GeminiElement(
            name="dataset-language",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:language/gmd:LanguageCode/@codeListValue",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:language/gmd:LanguageCode/@codeListValue",
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:language/gmd:LanguageCode/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:language/gmd:LanguageCode/text()",
            ],
            multiplicity="*",
        ),
        GeminiElement(
            name="topic-category",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:topicCategory/gmd:MD_TopicCategoryCode/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:topicCategory/gmd:MD_TopicCategoryCode/text()",
            ],
            multiplicity="*",
        ),
        GeminiElement(
            name="extent-controlled",
            search_paths=[
            ],
            multiplicity="*",
        ),
        GeminiElement(
            name="extent-free-text",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicDescription/gmd:geographicIdentifier/gmd:MD_Identifier/gmd:code/gco:CharacterString/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/srv:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicDescription/gmd:geographicIdentifier/gmd:MD_Identifier/gmd:code/gco:CharacterString/text()",
            ],
            multiplicity="*",
        ),
        GeminiElement(
            name="bbox-west-long",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox/gmd:westBoundLongitude/gco:Decimal/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/srv:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox/gmd:westBoundLongitude/gco:Decimal/text()",
            ],
            multiplicity="1",
        ),
        GeminiElement(
            name="bbox-east-long",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox/gmd:eastBoundLongitude/gco:Decimal/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/srv:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox/gmd:eastBoundLongitude/gco:Decimal/text()",
            ],
            multiplicity="1",
        ),
        GeminiElement(
            name="bbox-north-lat",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox/gmd:northBoundLatitude/gco:Decimal/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/srv:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox/gmd:northBoundLatitude/gco:Decimal/text()",
            ],
            multiplicity="1",
        ),
        GeminiElement(
            name="bbox-south-lat",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox/gmd:southBoundLatitude/gco:Decimal/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/srv:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox/gmd:southBoundLatitude/gco:Decimal/text()",
            ],
            multiplicity="1",
        ),
        GeminiElement(
            name="temporal-extent-begin",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:temporalElement/gmd:EX_TemporalExtent/gmd:extent/gml:TimePeriod/gml:beginPosition/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/srv:extent/gmd:EX_Extent/gmd:temporalElement/gmd:EX_TemporalExtent/gmd:extent/gml:TimePeriod/gml:beginPosition/text()",
            ],
            multiplicity="0..1",
        ),
        GeminiElement(
            name="temporal-extent-end",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:temporalElement/gmd:EX_TemporalExtent/gmd:extent/gml:TimePeriod/gml:endPosition/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/srv:extent/gmd:EX_Extent/gmd:temporalElement/gmd:EX_TemporalExtent/gmd:extent/gml:TimePeriod/gml:endPosition/text()",
            ],
            multiplicity="0..1",
        ),
        GeminiElement(
            name="vertical-extent",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:verticalElement/gmd:EX_VerticalExtent",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/srv:extent/gmd:EX_Extent/gmd:verticalElement/gmd:EX_VerticalExtent",
            ],
            multiplicity="0..1",
        ),
        GeminiElement(
            name="coupled-resource",
            search_paths=[
                "gmd:identificationInfo/srv:SV_ServiceIdentification/srv:operatesOn/@xlink:href",
            ],
            multiplicity="*",
        ),
        GeminiElement(
            name="additional-information-source",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:supplementalInformation/gco:CharacterString/text()",
            ],
            multiplicity="0..1",
        ),
        GeminiDataFormat(
            name="data-format",
            search_paths=[
                "gmd:distributionInfo/gmd:MD_Distribution/gmd:distributionFormat/gmd:MD_Format",
            ],
            multiplicity="*",
        ),
        GeminiResourceLocator(
            name="resource-locator",
            search_paths=[
                "gmd:distributionInfo/gmd:MD_Distribution/gmd:transferOptions/gmd:MD_DigitalTransferOptions/gmd:onLine/gmd:CI_OnlineResource",
            ],
            multiplicity="*",
        ),
        GeminiElement(
            name="conformity-specification",
            search_paths=[
                "gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:report/gmd:DQ_DomainConsistency/gmd:result/gmd:DQ_ConformanceResult/gmd:specification",
            ],
            multiplicity="0..1",
        ),
        GeminiElement(
            name="conformity-pass",
            search_paths=[
                "gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:report/gmd:DQ_DomainConsistency/gmd:result/gmd:DQ_ConformanceResult/gmd:pass/gco:Boolean/text()",
            ],
            multiplicity="0..1",
        ),
        GeminiElement(
            name="conformity-explanation",
            search_paths=[
                "gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:report/gmd:DQ_DomainConsistency/gmd:result/gmd:DQ_ConformanceResult/gmd:explanation/gco:CharacterString/text()",
            ],
            multiplicity="0..1",
        ),
        GeminiElement(
            name="lineage",
            search_paths=[
                "gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:lineage/gmd:LI_Lineage/gmd:statement/gco:CharacterString/text()",
            ],
            multiplicity="0..1",
        )
    ]

    def infer_values(self, values):
        # Todo: Infer name.
        self.infer_date_released(values)
        self.infer_date_updated(values)
        self.infer_url(values)
        # Todo: Infer resources.
        self.infer_tags(values)
        self.infer_publisher(values)
        self.infer_contact(values)
        self.infer_contact_email(values)
        return values

    def infer_date_released(self, values):
        value = ''
        for date in values['dataset-reference-date']:
            if date['type'] == 'publication':
                value = date['value']
                break
        values['date-released'] = value

    def infer_date_updated(self, values):
        value = ''
        # Todo: Use last of several multiple revision dates.
        for date in values['dataset-reference-date']:
            if date['type'] == 'revision':
                value = date['value']
                break
        values['date-updated'] = value

    def infer_url(self, values):
        value = ''
        for locator in values['resource-locator']:
            if locator['function'] == 'information':
                value = locator['url']
                break
        values['url'] = value

    def infer_tags(self, values):
        value = []
        value += values['keyword-inspire-theme']
        value += values['keyword-controlled-other']
        value += values['keyword-free-text']
        value = list(set(value))
        values['tags'] = value

    def infer_publisher(self, values):
        value = ''
        for responsible_party in values['responsible-organisation']:
            if responsible_party['role'] == 'publisher':
                value = responsible_party['organisation-name']
            if value:
                break
        values['publisher'] = value

    def infer_contact(self, values):
        value = ''
        for responsible_party in values['responsible-organisation']:
            value = responsible_party['organisation-name']
            if value:
                break
        values['contact'] = value

    def infer_contact_email(self, values):
        value = ''
        for responsible_party in values['responsible-organisation']:
            value = responsible_party['contact-info']['email']
            if value:
                break
        values['contact-email'] = value


class HarvestedDocument(DomainObject):

    def read_values(self):
        if "gmd:MD_Metadata" in self.content:
            gemini_document = GeminiDocument(self.content)
        else:
            raise HarvesterError, "Can't identify type of document content: %s" % self.content
        return gemini_document.read_values()


harvest_source_table = Table('harvest_source', metadata,
        Column('id', types.UnicodeText, primary_key=True, default=make_uuid),
        Column('url', types.UnicodeText, unique=True, nullable=False),
        Column('description', types.UnicodeText, default=u''),
        Column('user_ref', types.UnicodeText, default=u''),
        Column('publisher_ref', types.UnicodeText, default=u''),
        Column('created', DateTime, default=datetime.datetime.utcnow),
)

harvesting_job_table = Table('harvesting_job', metadata,
        Column('id', types.UnicodeText, primary_key=True, default=make_uuid),
        Column('status', types.UnicodeText, default=u'New', nullable=False),
        Column('created', DateTime, default=datetime.datetime.utcnow),
        Column('user_ref', types.UnicodeText, nullable=False),
        Column('report', JsonType),
        Column('errors', types.UnicodeText, default=u''),
        Column('source_id', types.UnicodeText, ForeignKey('harvest_source.id')),
)

harvested_document_table = Table('harvested_document', metadata,
        Column('id', types.UnicodeText, primary_key=True, default=make_uuid),
        Column('guid', types.UnicodeText, default=''),
        Column('created', DateTime, default=datetime.datetime.utcnow),
        Column('content', types.UnicodeText, nullable=False),
        Column('source_id', types.UnicodeText, ForeignKey('harvest_source.id')),
        Column('package_id', types.UnicodeText, ForeignKey('package.id')),
)


mapper(HarvestedDocument, harvested_document_table, properties={
    'package':relation(Package),
})

mapper(HarvestingJob, harvesting_job_table, properties={
    'source':relation(HarvestSource),
})

mapper(HarvestSource, harvest_source_table, properties={ 
    'documents': relation(HarvestedDocument,
        backref='source',
    #    cascade='all, delete, delete-orphan',
    )
})

