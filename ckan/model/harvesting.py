import logging
import datetime
from meta import *
from lxml import etree
import urllib2

from types import make_uuid
from types import JsonType
from core import *
from domain_object import DomainObject

log = logging.getLogger(__name__)

__all__ = [
    'HarvestSource', 'harvest_source_table',
    'HarvestingJob', 'harvesting_job_table',
    'HarvestedDocument', 'harvested_document_table',
]

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

    def write_package(self, document):
        from ckan.lib.base import _
        import ckan.forms
        import ckan.model as model
        package = None
        # Read data for package.
        values = document.read_attributes()
        package_data = {
            'name': values['guid'],
            'title': values['title'],
            'extras': values,
        }
        # Create package from data.
        try:
            user_editable_groups = []
            fs = ckan.forms.get_standard_fieldset(user_editable_groups=user_editable_groups)
            try:
                fa_dict = ckan.forms.edit_package_dict(ckan.forms.get_package_dict(fs=fs, user_editable_groups=user_editable_groups), package_data)
            except ckan.forms.PackageDictFormatError, inst:
                msg = 'Package format incorrect: %s' % str(inst)
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
                    msg = 'Validation error: %r' % repr(fs.errors)
                    raise Exception, msg
        except Exception, inst:
            log.exception(inst)
            model.Session.rollback()
            msg = 'Error creating object from data %s: %r' % (str(package_data), inst)
            log.error(msg)
            raise Exception, msg
        return package


class HarvestingJob(DomainObject):

    def harvest_documents(self):
        self.set_status_running()
        self.get_report()
        self.save()
        try:
            content = self.get_source_content()
        except urllib2.URLError, inst:
            msg = "Unable to read registered URL: %s" % inst
            self.report_error(msg)
        else:
            source_type = self.detect_source_type(content)
            if source_type == None:
                self.report_error("Unable to detect source type from content: %s" % content)
            elif source_type == 'doc':
                self.harvest_document(url=self.source.url, content=content)
            elif source_type == 'csw':
                self.harvest_csw_documents(url=self.source.url)
            else:
                raise Exception, "Source type '%s' not supported." % source_type
            if not self.report_has_errors():
                self.set_status_success()
            else:
                self.set_status_error()
            self.save()
        return self.report

    def report_error(self, msg):
        self.get_report()['errors'].append(msg)
        self.save()

    def report_package(self, msg):
        self.get_report()['packages'].append(msg)
        self.save()

    def get_report(self):
        if self.report == None:
            self.report = {
                'packages': [],
                'errors': [],
            }
        return self.report

    def report_has_errors(self):
        return bool(self.get_report()['errors'])

    def get_source_content(self):
        source = urllib2.urlopen(self.source.url)
        content = source.read()
        return content

    def detect_source_type(self, content):
        if "<gmd:MD_Metadata" in content:
            return 'doc'
        if "<ows:ExceptionReport" in content:
            return 'csw'
        # Todo: Detect WAF.

    def harvest_document(self, url, content):
        try:
            self.validate_content(content)
            document = self.save_content(url, content)
            package = self.source.write_package(document)
            self.report_package(package.id)
        except CswError, inst:
            msg = "Error reading harvested content: %s" % content
            self.report_error(msg)

    def harvest_csw_documents(self, url):
        from ckan.lib.cswclient import CswClient
        csw_client = CswClient(base_url=url)
        records = csw_client.get_records()
        for record in records:
            self.harvest_document(url=url, content=record)

    def validate_content(self, content):
        pass

    def save_content(self, url, content):
        return HarvestedDocument.create_save(url=url, content=content)

    def set_status_success(self):
        self.set_status(u"Success")

    def set_status_running(self):
        self.set_status(u"Running")

    def set_status_error(self):
        self.set_status(u"Error")

    def set_status(self, status):
        self.status = status


class GeminiAttribute(object):

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

    def __init__(self, name, xpaths=[], multiplicity="*"):
        self.name = name
        self.xpaths = xpaths
        self.multiplicity = multiplicity

    def read_attribute(self, tree):
        if type(self.xpaths) != type([]):
            xpaths = [self.xpaths]
        else:
            xpaths = self.xpaths
        values = []
        for xpath in xpaths:
            elements = self.read_xpath(tree, xpath)
            if len(elements) == 0:
                pass
            else:
                for e in elements:
                    if (type(e) == etree._ElementStringResult):
                        value = str(e)
                    #elif e.tag == '{http://www.isotc211.org/2005/gco}CharacterString':
                    #    value = e.text
                    #elif e.tag == '{http://www.isotc211.org/2005/gco}Decimal':
                    #    value = e.text
                    #elif e.tag == '{http://www.isotc211.org/2005/gmd}MD_TopicCategoryCode':
                    #    value = e.text
                    #elif e.tag == '{http://www.isotc211.org/2005/gmd}URL':
                    #    value = e.text
                    else:
                        value = etree.tostring(e, pretty_print=False)
                    values.append(value)
            if values:
                break
        if self.multiplicity == "1":
            if values:
                values = values[0]
            else:
                raise Exception, "Value not found for attribute '%s'" % self.name
        elif self.multiplicity == "0..1":
            if values:
                values = values[0]
            else:
                values = ""
        return values

    def read_xpath(self, tree, xpath):
        return tree.xpath(xpath, namespaces=self.namespaces)


class MetadataDocument(object):

    def __init__(self, content):
        self.content = content

    def read_attributes(self):
        values = {}
        tree = self.get_content_tree()
        for a in self.attributes:
            values[a.name] = a.read_attribute(tree)
        return values
        
    def get_content_tree(self):
        parser = etree.XMLParser(remove_blank_text=True)
        return etree.fromstring(self.content, parser=parser)


class GeminiDocument(MetadataDocument):

    # Attribute specifications from "XPaths for GEMINI" by Peter Parslow.
    # - multiplicity options: "0", "1", "*", "1..*"

    attributes = [
        GeminiAttribute(
            name="guid",
            xpaths="gmd:fileIdentifier/gco:CharacterString/text()",
            multiplicity="0..1",
        ),GeminiAttribute(
            name="metadata-language",
            xpaths=[
                "gmd:language/gmd:LanguageCode/@codeListValue",
                "gmd:language/gmd:LanguageCode/text()",
            ],
            multiplicity="1",
        ),GeminiAttribute(
            name="resource-type",
            xpaths=[
                "gmd:hierarchyLevel/gmd:MD_ScopeCode/@codeListValue",
                "gmd:hierarchyLevel/gmd:MD_ScopeCode/text()",
            ],
            multiplicity="1",
        ),GeminiAttribute(
            name="metadata-point-of-contact",
            xpaths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:pointOfContact/gmd:CI_ResponsibleParty",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:pointOfContact/gmd:CI_ResponsibleParty",
            ],
            multiplicity="1..*",
        ),GeminiAttribute(
            name="metadata-date",
            xpaths=[
                "gmd:dateStamp/gco:Date/text()",
                "gmd:dateStamp/gco:DateTime/text()",
            ],
            multiplicity="1",
        ),GeminiAttribute(
            name="spatial-reference-system",
            xpaths=[
                "gmd:referenceSystemInfo/gmd:MD_ReferenceSystem",
            ],
            multiplicity="0..1",
        ),GeminiAttribute(
            name="title",
            xpaths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:title/gco:CharacterString/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:citation/gmd:CI_Citation/gmd:title/gco:CharacterString/text()",
            ],
            multiplicity="1",
        ),GeminiAttribute(
            name="alternative-title",
            xpaths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:alternativeTitle/gco:CharacterString/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:citation/gmd:CI_Citation/gmd:alternativeTitle/gco:CharacterString/text()",
            ],
            multiplicity="*",
        ),GeminiAttribute(
            name="dataset-reference-date",
            xpaths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:date/gmd:CI_Date",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:citation/gmd:CI_Citation/gmd:date/gmd:CI_Date",
            ],
            multiplicity="*",
        #),GeminiAttribute(
        #    name="dataset-reference-date-type",
        #    xpaths=[
        #        "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:date/gmd:CI_Date/gmd:dateType/gmd:CI_DateTypeCode/@codeListValue",
        #        "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:citation/gmd:CI_Citation/gmd:date/gmd:CI_Date/gmd:dateType/gmd:CI_DateTypeCode",
        #    ],
        #    multiplicity="*",

        # Todo: Suggestion from PP not to bother pulling this into the package.
        ),GeminiAttribute(
            name="unique-resource-identifier",
            xpaths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:identifier/gmd:RS_Identifier",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:citation/gmd:CI_Citation/gmd:identifier/gmd:RS_Identifier",
            ],
            multiplicity="1",
        ),GeminiAttribute(
            name="abstract",
            xpaths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:abstract/gco:CharacterString/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:abstract/gco:CharacterString/text()",
            ],
            multiplicity="1",
        ),GeminiAttribute(
            name="responsible-organisation",
            xpaths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:pointOfContact/gmd:CI_ResponsibleParty",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:pointOfContact/gmd:CI_ResponsibleParty",
            ],
            multiplicity="1..*",
        ),GeminiAttribute(
            name="frequency-of-update",
            xpaths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:resourceMaintenance/gmd:MD_MaintenanceInformation/gmd:maintenanceAndUpdateFrequency/gmd:MD_MaintenanceFrequencyCode/@codeListValue",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:resourceMaintenance/gmd:MD_MaintenanceInformation/gmd:maintenanceAndUpdateFrequency/gmd:MD_MaintenanceFrequencyCode/@codeListValue",

                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:resourceMaintenance/gmd:MD_MaintenanceInformation/gmd:maintenanceAndUpdateFrequency/gmd:MD_MaintenanceFrequencyCode/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:resourceMaintenance/gmd:MD_MaintenanceInformation/gmd:maintenanceAndUpdateFrequency/gmd:MD_MaintenanceFrequencyCode/text()",
            ],
            multiplicity="0..1",
        ),GeminiAttribute(
            name="keyword-inspire-theme",
            xpaths=[
                #"gmd:identificationInfo/gmd:MD_DataIdentification/gmd:descriptiveKeywords/gmd:MD_Keywords[some GEMET citation1]/gmd:keyword/gco:CharacterString",
                #"gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:descriptiveKeywords/gmd:MD_Keywords[some GEMET citation1]/gmd:keyword/gco:CharacterString",
            ],
            multiplicity="*",
        ),GeminiAttribute(
            name="keyword-controlled-other",
            xpaths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:descriptiveKeywords/gmd:MD_Keywords/gmd:keyword/gco:CharacterString/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:descriptiveKeywords/gmd:MD_Keywords/gmd:keyword/gco:CharacterString/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/srv:keywords/gmd:MD_Keywords/gmd:keyword/gco:CharacterString/text()",
            ],
            multiplicity="*",
        ),GeminiAttribute(
            name="keyword-free-text",
            xpaths=[
            ],
            multiplicity="*",
        ),GeminiAttribute(
            name="limitations-on-public-access",
            xpaths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:resourceConstraints/gmd:MD_LegalConstraints/gmd:accessConstraints/gmd:otherConstraints/gco:CharacterString/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:resourceConstraints/gmd:MD_LegalConstraints/gmd:accessConstraints/gmd:otherConstraints/gco:CharacterString/text()",
            ],
            multiplicity="1..*",
        ),GeminiAttribute(
            name="use-constraints",
            xpaths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:resourceConstraints/gmd:MD_Constraints/gmd:useLimitation/gco:CharacterString/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:resourceConstraints/gmd:MD_Constraints/gmd:useLimitation/gco:CharacterString/text()",
            ],
            multiplicity="*",
        ),GeminiAttribute(
            name="spatial-data-service-type",
            xpaths=[
                "gmd:identificationInfo/srv:SV_ServiceIdentification/srv:serviceType/gco:LocalName",
            ],
            multiplicity="0..1",
        ),GeminiAttribute(
            name="spatial-resolution",
            xpaths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:spatialResolution/gmd:MD_Resolution/gmd:distance/gco:Distance",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:spatialResolution/gmd:MD_Resolution/gmd:distance/gco:Distance",
            ],
            multiplicity="0..1",
        ),GeminiAttribute(
            name="spatial-resolution-units",
            xpaths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:spatialResolution/gmd:MD_Resolution/gmd:distance/gco:Distance/@uom",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:spatialResolution/gmd:MD_Resolution/gmd:distance/gco:Distance/@uom",
            ],
            multiplicity="0..1",
        ),GeminiAttribute(
            name="equivalent-scale",
            xpaths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:spatialResolution/gmd:MD_Resolution/gmd:equivalentScale/gmd:MD_RepresentativeFraction/gmd:denominator/gco:Integer/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:spatialResolution/gmd:MD_Resolution/gmd:equivalentScale/gmd:MD_RepresentativeFraction/gmd:denominator/gco:Integer/text()",
            ],
            multiplicity="*",
        ),GeminiAttribute(
            name="dataset-language",
            xpaths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:language/gmd:LanguageCode/@codeListValue",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:language/gmd:LanguageCode/@codeListValue",
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:language/gmd:LanguageCode/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:language/gmd:LanguageCode/text()",
            ],
            multiplicity="*",
        ),GeminiAttribute(
            name="topic-category",
            xpaths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:topicCategory/gmd:MD_TopicCategoryCode/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:topicCategory/gmd:MD_TopicCategoryCode/text()",
            ],
        ),GeminiAttribute(
            name="extent-controlled",
            xpaths=[
            ],
            multiplicity="*",
        ),GeminiAttribute(
            name="extent-free-text",
            xpaths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicDescription/gmd:geographicIdentifier/gmd:MD_Identifier/gmd:code/gco:CharacterString/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/srv:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicDescription/gmd:geographicIdentifier/gmd:MD_Identifier/gmd:code/gco:CharacterString/text()",
            ],
            multiplicity="*",
        ),GeminiAttribute(
            name="bbox-west-long",
            xpaths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox/gmd:westBoundLongitude/gco:Decimal/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/srv:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox/gmd:westBoundLongitude/gco:Decimal/text()",
            ],
            multiplicity="1",
        ),GeminiAttribute(
            name="bbox-east-long",
            xpaths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox/gmd:eastBoundLongitude/gco:Decimal/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/srv:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox/gmd:eastBoundLongitude/gco:Decimal/text()",
            ],
            multiplicity="1",
        ),GeminiAttribute(
            name="bbox-north-lat",
            xpaths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox/gmd:northBoundLatitude/gco:Decimal/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/srv:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox/gmd:northBoundLatitude/gco:Decimal/text()",
            ],
            multiplicity="1",
        ),GeminiAttribute(
            name="bbox-south-lat",
            xpaths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox/gmd:southBoundLatitude/gco:Decimal/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/srv:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox/gmd:southBoundLatitude/gco:Decimal/text()",
            ],
            multiplicity="1",
        ),GeminiAttribute(
            name="temporal-extent-begin",
            xpaths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:temporalElement/gmd:EX_TemporalExtent/gmd:extent/gml:TimePeriod/gml:beginPosition/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/srv:extent/gmd:EX_Extent/gmd:temporalElement/gmd:EX_TemporalExtent/gmd:extent/gml:TimePeriod/gml:beginPosition/text()",
            ],
            multiplicity="0..1",
        ),GeminiAttribute(
            name="temporal-extent-end",
            xpaths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:temporalElement/gmd:EX_TemporalExtent/gmd:extent/gml:TimePeriod/gml:endPosition/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/srv:extent/gmd:EX_Extent/gmd:temporalElement/gmd:EX_TemporalExtent/gmd:extent/gml:TimePeriod/gml:endPosition/text()",
            ],
            multiplicity="0..1",
        ),GeminiAttribute(
            name="vertical-extent",
            xpaths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:verticalElement/gmd:EX_VerticalExtent",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/srv:extent/gmd:EX_Extent/gmd:verticalElement/gmd:EX_VerticalExtent",
            ],
            multiplicity="0..1",
        ),GeminiAttribute(
            name="coupled-resource",
            xpaths=[
                "gmd:identificationInfo/srv:SV_ServiceIdentification/srv:operatesOn/@xlink:href",
            ],
            multiplicity="*",
        ),GeminiAttribute(
            name="additional-information-source",
            xpaths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:supplementalInformation/gco:CharacterString/text()",
            ],
            multiplicity="0..1",
        ),GeminiAttribute(
            name="data-format",
            xpaths=[
                "gmd:distributionInfo/gmd:MD_Distribution/gmd:distributionFormat/gmd:MD_Format",
            ],
            multiplicity="*",
        ),GeminiAttribute(
            name="resource-locator",
            xpaths=[
                "gmd:distributionInfo/gmd:MD_Distribution/gmd:transferOptions/gmd:MD_DigitalTransferOptions/gmd:onLine/gmd:CI_OnlineResource/gmd:linkage/gmd:URL/text()",
            ],
            multiplicity="*",
        ),GeminiAttribute(
            name="conformity-specification",
            xpaths=[
                "gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:report/gmd:DQ_DomainConsistency/gmd:result/gmd:DQ_ConformanceResult/gmd:specification",
            ],
            multiplicity="0..1",
        ),GeminiAttribute(
            name="conformity-pass",
            xpaths=[
                "gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:report/gmd:DQ_DomainConsistency/gmd:result/gmd:DQ_ConformanceResult/gmd:pass/gco:Boolean/text()",
            ],
            multiplicity="0..1",
        ),GeminiAttribute(
            name="conformity-explanation",
            xpaths=[
                "gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:report/gmd:DQ_DomainConsistency/gmd:result/gmd:DQ_ConformanceResult/gmd:explanation/gco:CharacterString/text()",
            ],
            multiplicity="0..1",
        ),GeminiAttribute(
            name="lineage",
            xpaths=[
                "gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:lineage/gmd:LI_Lineage/gmd:statement/gco:CharacterString/text()",
            ],
            multiplicity="0..1",
        #),GeminiAttribute(
        #    name="resource-locator-description",
        #    xpaths="gmd:distributionInfo/gmd:MD_Distribution/gmd:transferOptions/gmd:MD_DigitalTransferOptions/gmd:onLine/gmd:CI_OnlineResource/gmd:function/gmd:CI_OnLineFunctionCode/@codeListValue",
        )
    ]



class HarvestedDocument(DomainObject):

    def read_attributes(self):
        if "gmd:MD_Metadata" in self.content:
            doc = GeminiDocument(self.content)
        else:
            raise Exception, "Can't identify type of document content: %s" % self.content
        return doc.read_attributes()


harvest_source_table = Table('harvest_source', metadata,
        Column('id', types.UnicodeText, primary_key=True, default=make_uuid),
        Column('status', types.UnicodeText, default=u'New', nullable=False),
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
        # Todo: Migration script to delete old column and add new column.
        Column('report', JsonType),
        Column('source_id', types.UnicodeText, ForeignKey('harvest_source.id')),
)

harvested_document_table = Table('harvested_document', metadata,
        Column('id', types.UnicodeText, primary_key=True, default=make_uuid),
        Column('created', DateTime, default=datetime.datetime.utcnow),
        Column('url', types.UnicodeText, nullable=False),
        Column('content', types.UnicodeText, nullable=False),
)

mapper(HarvestedDocument, harvested_document_table, properties={ })

mapper(HarvestingJob, harvesting_job_table, properties={
    'source':relation(HarvestSource),
})

mapper(HarvestSource, harvest_source_table, properties={ 
})




