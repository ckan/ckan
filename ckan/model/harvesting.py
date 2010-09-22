import logging
import datetime
from meta import *
from lxml import etree
import urllib2

from types import make_uuid
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
        doc_data = document.read_attributes()
        package_data = {
            'name': doc_data['guid'],
            'title': doc_data['title'],
            'extras': doc_data,
        }
        # Create package from data.
        try:
            fs = ckan.forms.get_standard_fieldset()
            try:
                fa_dict = ckan.forms.edit_package_dict(ckan.forms.get_package_dict(fs=fs), package_data)
            except ckan.forms.PackageDictFormatError, inst:
                log.error('Package format incorrect: %s' % str(inst))
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
                    log.error('Validation error: %r' % repr(fs.errors))
        except Exception, inst:
            log.exception(inst)
            model.Session.rollback()
            log.error('Exception creating object from data %s: %r' % (str(package_data), inst))
            raise
        return package


class HarvestingJob(DomainObject):

    def harvest_documents(self):
        try:
            content = self.get_source_content()
            source_type = self.detect_source_type(content)
            if source_type == 'doc':
                self.harvest_document(url=self.source.url, content=content)
            elif source_type == 'csw':
                pass
            elif source_type == 'waf':
                pass
            else:
                raise Exception, "Source type '%s' not supported." % source_type
        except Exception, inst:
            import traceback
            self.report = "Couldn't harvest documents: %s" % traceback.format_exc() 
            self.set_status_error()
            self.save()
        else:
            self.write_report()
            self.set_status_success()
            self.save()
        return self.report

    def get_source_content(self):
        source = urllib2.urlopen(self.source.url)
        content = source.read()
        return content

    def detect_source_type(self, content):
        if "<gmd:MD_Metadata" in content:
            return 'doc'
        # Todo: Detect CSW.
        # Todo: Detect WAF.
        raise Exception, "Harvest source type can't be detected from content: %s" % content

    def harvest_document(self, url, content):
        self.validate_content(content)
        document = self.save_content(url, content)
        package = self.source.write_package(document)

    def validate_content(self, content):
        pass

    def save_content(self, url, content):
        return HarvestedDocument.create_save(url=url, content=content)

    def write_report(self):
        self.report = u"Success"

    def set_status_success(self):
        self.set_status(u"Success")

    def set_status_error(self):
        self.set_status(u"Error")

    def set_status(self, status):
        self.status = status


class HarvestedDocument(DomainObject):

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

    # Attribute specifications from "XPaths for GEMINI" by Peter Parslow.
    # - multiplicity options: "0", "1", "*", "1..*"
    attribute_specs = [
        {
            "name": "guid",
            "xpath": "gmd:fileIdentifier/gco:CharacterString",
            "multiplicity": "0..1",
        },{
            "name": "metadata-language",
            "xpath": [
                "gmd:language/gmd:LanguageCode/@codeListValue",
                "gmd:language/gmd:LanguageCode",
            ],
            "multiplicity": "1",
        },{
            "name": "resource-type",
            "xpath": [
                "gmd:hierarchyLevel/gmd:MD_ScopeCode/@codeListValue",
                "gmd:hierarchyLevel/gmd:MD_ScopeCode",
            ],
            "multiplicity": "1",
        },{
            "name": "metadata-point-of-contact",
            "xpath": [
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:pointOfContact/gmd:CI_ResponsibleParty//gco:CharacterString",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:pointOfContact/gmd:CI_ResponsibleParty//gco:CharacterString",
            ],
            "multiplicity": "1..*",
        },{
            "name": "metadata-date",
            "xpath": [
                "gmd:dateStamp/gmd:Date",
                "gmd:dateStamp/gmd:DateTime",
            ],
            "multiplicity": "1",
        },{
            "name": "spatial-reference-system",
            "xpath": [
                "gmd:referenceSystemInfo/ gmd:MD_ReferenceSystem",
            ],
            "multiplicity": "0..1",
        },{
            "name": "title",
            "xpath": [
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:title/gco:CharacterString",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:citation/gmd:CI_Citation/gmd:title/gco:CharacterString",
            ],
            "multiplicity": "1",
        },{
            "name": "alternative-title",
            "xpath": [
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:alternativeTitle/gco:CharacterString",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:citation/gmd:CI_Citation/gmd:alternativeTitle/gco:CharacterString",
            ],
            "multiplicity": "*",
        },{
            "name": "dataset-reference-date",
            "xpath": [
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:date/gmd:CI_Date/gmd:date/gco:Date",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:citation/gmd:CI_Citation/gmd:date/gmd:CI_Date/gmd:date/gco:Date",
            ],
            "multiplicity": "*",
        },{
            "name": "dataset-reference-date-type",
            "xpath": [
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:date/gmd:CI_Date/gmd:dateType/gmd:CI_DateTypeCode/@codeListValue",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:citation/gmd:CI_Citation/gmd:date/gmd:CI_Date/gmd:dateType/gmd:CI_DateTypeCode",
            ],
            "multiplicity": "*",
        },{
            "name": "abstract",
            "xpath": [
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:abstract/gco:CharacterString",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:abstract/gco:CharacterString",
            ],
            "multiplicity": "*",
        },{
            "name": "bbox-west-long",
            "xpath": [
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox/gmd:westBoundLongitude/gco:Decimal",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox/gmd:westBoundLongitude/gco:Decimal",
            ],
        },{
            "name": "bbox-east-long",
            "xpath": [
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox/gmd:eastBoundLongitude/gco:Decimal",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox/gmd:eastBoundLongitude/gco:Decimal",
            ],
        },{
            "name": "bbox-north-lat",
            "xpath": [
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox/gmd:northBoundLatitude/gco:Decimal",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox/gmd:northBoundLatitude/gco:Decimal",
            ],
        },{
            "name": "bbox-south-lat",
            "xpath": [
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox/gmd:southBoundLatitude/gco:Decimal",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox/gmd:southBoundLatitude/gco:Decimal",
            ],
        },{
            "name": "keyword",
            "xpath": [
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:descriptiveKeywords/gmd:MD_Keywords/gmd:keyword/gco:CharacterString",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/srv:keywords/gmd:MD_Keywords/gmd:keyword/gco:CharacterString",
                "gmd:identificationInfo//gmd:MD_DataIdentification/gmd:descriptiveKeywords/gmd:MD_Keywords",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/srv:keywords/gmd:MD_Keywords",
            ],
        },{
            "name": "use-constraints",
            "xpath": [
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:resourceConstraints/gmd:MD_Constraints/gmd:useLimitation/gco:CharacterString",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:resourceConstraints/gmd:MD_Constraints/gmd:useLimitation/gco:CharacterString",
            ],
        },{
            "name": "topic-category",
            "xpath": [
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:topicCategory/gmd:MD_TopicCategoryCode",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:topicCategory/gmd:MD_TopicCategoryCode",
            ],
        },{
            "name": "resource-locator",
            "xpath": [
                "gmd:distributionInfo/gmd:MD_Distribution/gmd:transferOptions/gmd:MD_DigitalTransferOptions/gmd:onLine/gmd:CI_OnlineResource/gmd:linkage/gmd:URL",
                "gmd:distributionInfo/gmd:MD_Distribution/gmd:transferOptions/gmd:MD_DigitalTransferOptions/gmd:onLine/gmd:CI_OnlineResource/gmd:linkage",
            ],
        },{
            "name": "resource-locator-description",
            "xpath": "gmd:distributionInfo/gmd:MD_Distribution/gmd:transferOptions/gmd:MD_DigitalTransferOptions/gmd:onLine/gmd:CI_OnlineResource/gmd:function/gmd:CI_OnLineFunctionCode/@codeListValue",
        }
    ]

    def read_attributes(self):
        attributes = {}
        tree = self.get_content_tree()
        for attr_spec in self.attribute_specs:
            attr_name = attr_spec["name"]
            attr_xpaths = attr_spec["xpath"]
            attr_values = self.read_attribute(tree, attr_xpaths)
            attributes[attr_name] = attr_values
        return attributes
        
    def get_content_tree(self):
        return etree.fromstring(self.content)

    def read_attribute(self, tree, xpaths):
        if type(xpaths) != type([]):
            xpaths = [xpaths]
        values = []
        for xpath in xpaths:
            elements = self.read_xpath(tree, xpath)
            if len(elements) == 0:
                pass
            else:
                for e in elements:
                    if (type(e) == etree._ElementStringResult):
                        value = str(e)
                    elif e.tag == '{http://www.isotc211.org/2005/gco}CharacterString':
                        value = e.text
                    elif e.tag == '{http://www.isotc211.org/2005/gco}Decimal':
                        value = e.text
                    elif e.tag == '{http://www.isotc211.org/2005/gmd}MD_TopicCategoryCode':
                        value = e.text
                    elif e.tag == '{http://www.isotc211.org/2005/gmd}URL':
                        value = e.text
                    else:
                        value = etree.tostring(e, pretty_print=True)
                    values.append(value)
            if values:
                break
        return values

    def read_xpath(self, tree, xpath):
        return tree.xpath(xpath, namespaces=self.namespaces)

    
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
        Column('report', types.UnicodeText, default=u''),    
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




