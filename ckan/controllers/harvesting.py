"""\
Note: This isn't a normal Pylons controller so it should be moved to ``lib``

Eventually, harvesting code should move to ckanext-csw
"""
import urllib2
from lxml import etree

from pylons.i18n import _

from ckan.lib.base import *
from ckan.lib.helpers import literal
from ckan.lib.cache import proxy_cache
from ckan.lib.package_saver import PackageSaver, ValidationException
from ckan.lib.package_saver import WritePackageFromBoundFieldset
from ckan.lib.base import BaseController
from ckan.plugins import PluginImplementations, IPackageController
from ckanext.harvest.model import HarvesterError, HarvesterUrlError, ValidationError
from ckanext.harvest.model import GeminiDocument
from ckanext.harvest.model import HarvestedDocument

import ckan.forms
from ckan.forms import GetPackageFieldset
from ckan.forms import GetEditFieldsetPackageData
import ckan.model as model
import ckan.authz
import ckan.rating
import ckan.misc
from ckan.lib.munge import munge_title_to_name

log = __import__("logging").getLogger(__name__)

def gen_new_name(title):
    name = munge_title_to_name(title).replace('_', '-')
    while '--' in name:
        name = name.replace('--', '-')
    like_q = u"%s%%" % name
    pkg_query = model.Session.query(model.Package).filter(model.Package.name.ilike(like_q)).limit(100)
    taken = [pkg.name for pkg in pkg_query]
    if name not in taken:
        return name
    else:
        counter = 1
        while counter < 101:
            if name+str(counter) not in taken:
                return name+str(counter)
        return None

class HarvestingJobController(object):
    """\
    This is not a controller in the Pylons sense, just an object for managing
    harvesting.
    """
    def __init__(self, job, validator=None):
        self.job = job
        self.validator = validator

    def harvest_documents(self):
        try:
            content = self.get_content(self.job.source.url)
        except HarvesterUrlError, exception:
            msg = "Error harvesting source: %s" % exception
            self.job.report['errors'].append(msg)
        else:
            # @@@ This is very ugly. Essentially for remote (CSW) services
            # we purposely cause an error to detect what they are.
            # Likely a much better idea just to have a type in the
            # source table
            source_type = self.detect_source_type(content)
            if source_type not in ['doc', 'waf', 'csw']:
                if source_type == None:
                    self.job.report['errors'].append(
                        "Unable to detect source type from content",
                    )
                else:
                    self.job.report['errors'].append(
                        "Source type '%s' not supported" % source_type
                    )
            else:
                # @@@ We want a model where the harvesting returns
                # documents, then each document is parsed and errors
                # are associated with the document itself, and the 
                # documents are serialised afterwards I think.
                # Here everything is done in one go.
                if source_type == 'doc':
                    self.harvest_gemini_document(content)
                elif source_type == 'csw':
                    self.harvest_csw_documents(url=self.job.source.url)
                elif source_type == 'waf':
                    self.harvest_waf_documents(content)
        # Set the status based on the outcome
        if not self.job.report.get('errors', []):
            self.job.status = u"Success"
        elif self.job.report.get('added', []) and self.job.report.get('errors', []):
            self.job.status = u"Partial Success"
        elif not self.job.report.get('added', []) and not self.job.report.get('errors', []):
            self.job.status = u"No Change"
        elif not self.job.report.get('added', []) and self.job.report.get('errors', []):
            self.job.status = u"Failed"
        self.job.save()
        return self.job

    def write_package_from_gemini_string(self, content):
        """Create or update a Package based on some content that has
        come from a URL.

        Also store the raw content as a HarvestedDocument (with
        references to its source and its package)
        """
        # Look for previously harvested document matching Gemini GUID
        harvested_doc = None
        package = None
        gemini_document = GeminiDocument(content)
        gemini_values = gemini_document.read_values()
        gemini_guid = gemini_values['guid']
        harvested_documents = HarvestedDocument.filter(guid=gemini_guid).all()
        if len(harvested_documents) > 1:
            # A programming error; should never happen
            raise Exception(
                "More than one harvested document GUID %s" % gemini_guid
            )
        elif len(harvested_documents) == 1:
             # we've previously harvested this (i.e. it's an update)
            harvested_doc = harvested_documents[0]
            if harvested_doc.source is None:
                # The source has been deleted, we can re-use it
                log.info('This document existed from another source which was deleted, using your document instead')
                harvested_doc.source = self.job.source
                package = harvested_doc.package
                harvested_doc.save()
                package.save()
                return None
            if harvested_doc.source.id != self.job.source.id:
                # A 'user' error: there are two or more sources
                # pointing to the same harvested document
                if self.job.source.id is None:
                    raise Exception('You cannot have an unsaved job source')
                raise HarvesterError(
                    literal("Another source %s (publisher %s, user %s) is using metadata GUID %s" % (
                        harvested_doc.source.url,
                        harvested_doc.source.publisher_ref,
                        harvested_doc.source.user_ref,
                        gemini_guid,
                    ))
                )
            if harvested_doc.content == content:
                log.info("Document with GUID %s unchanged, skipping..." % (gemini_guid))
                return None
            else:
                log.info("Harvested document with GUID %s has changed, re-creating..." % (gemini_guid))
            log.info("Updating package for %s" % gemini_guid)
            package = harvested_doc.package
        else:
            log.info("No package with GEMINI guid %s found, let's create one" % gemini_guid)
        extras = {
            'published_by': int(self.job.source.publisher_ref or 0),
            'INSPIRE': 'True',
        }
        # Just add some of the metadata as extras, not the whole lot
        for name in [
            # Essentials
            'bbox-east-long', 
            'bbox-north-lat', 
            'bbox-south-lat', 
            'bbox-west-long', 
            'guid', 
            # Usefuls
            'spatial-reference-system',
            'dataset-reference-date',
            'resource-type',
            'metadata-language', # Language
            'metadata-date', # Released
        ]:
            extras[name] = gemini_values[name]
        extras['constraint'] = '; '.join(gemini_values.get("use-constraints", '')+gemini_values.get("limitations-on-public-access"))
        if gemini_values.has_key('temporal-extent-begin'):
            #gemini_values['temporal-extent-begin'].sort()
            extras['temporal_coverage-from'] = gemini_values['temporal-extent-begin']
        if gemini_values.has_key('temporal-extent-end'):
            #gemini_values['temporal-extent-end'].sort()
            extras['temporal_coverage-to'] = gemini_values['temporal-extent-end']
        package_data = {
            'title': gemini_values['title'],
            'notes': gemini_values['abstract'],
            'extras': extras,
            'tags': gemini_values['tags'],
        }
        if package is None or package.title != gemini_values['title']:
            name = gen_new_name(gemini_values['title'])
            if not name:
                name = gen_new_name(str(gemini_guid))
            if not name:
                raise Exception('Could not generate a unique name from the title or the GUID. Please choose a more unique title.')
            package_data['name'] = name
        resource_locator = gemini_values.get('resource-locator', []) and gemini_values['resource-locator'][0].get('url') or ''
        if resource_locator:
            package_data['resources'] = [
                {
                    'url': resource_locator,
                    'description': 'Resource locator',
                    'format': 'Unverified',
                },
                # These are generated in Drupal now
                #{
                #    'url': '%s/api/2/rest/harvesteddocument/%s/xml/%s.xml'%(
                #        config.get('ckan.api_url', '/').rstrip('/'),
                #        gemini_guid, 
                #        gemini_guid,
                #    ),
                #    'description': 'Source GEMINI 2 document',
                #    'format': 'XML',
                #},
                #{
                #    'url': '%s/api/rest/harvesteddocument/%s/html'%(
                #        config.get('ckan.api_url', '/').rstrip('/'),
                #        gemini_guid,
                #    ),
                #    'description': 'Formatted GEMINI 2 document', 
                #    'format': 'HTML',
                #},
            ]
        if package == None:
            # Create new package from data.
            package = self._create_package_from_data(package_data)
            log.info("Created new package ID %s with GEMINI guid %s", package.id, gemini_guid)
            harvested_doc = HarvestedDocument(
                content=content,
                guid=gemini_guid,
                package=package,
                source=self.job.source,
            )
            harvested_doc.save()
            if not harvested_doc.source_id:
                raise Exception('Failed to set the source for document %r'%harvested_doc.id)
            assert gemini_guid == package.documents[0].guid
            return package
        else:
            package = self._create_package_from_data(package_data, package = package)
            log.info("Updated existing package ID %s with existing GEMINI guid %s", package.id, gemini_guid)
            harvested_doc.content = content
            harvested_doc.source = self.job.source
            harvested_doc.save()
            if not harvested_doc.source_id:
                raise Exception('Failed to set the source for document %r'%harvested_doc.id)
            assert gemini_guid == package.documents[0].guid
            return package

    def get_content(self, url):
        try:
            http_response = urllib2.urlopen(url)
            return http_response.read() #decode_response(http_response)
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

    def harvest_gemini_document(self, gemini_string):
        try:
            xml = etree.fromstring(gemini_string)
            if self.validator is not None:
                # ww: sigh... encoding, decoding, encoding, decoding
                # convention really should be, parse into etree at
                # the first opportunity and then only pass that
                # around internally...
                # jg: I've modified the code to use the document from
                # the elementree parse, hopefully avoiding one encoding
                # guess
                valid, messages = self.validator.isvalid(xml)
                if not valid:
                    raise ValidationError(*messages)
            unicode_gemini_string = etree.tostring(xml, encoding=unicode, pretty_print=True)
            package = self.write_package_from_gemini_string(unicode_gemini_string) 
        except HarvesterError, exception:
            for msg in [str(x) for x in exception.args]:
                log.error(msg)
                self.job.report['errors'].append(msg)
        except Exception, e:
            raise
            self.job.report['errors'].append('se: %r'%str(e))
        else:
            if package:
                self.job.report['added'].append(package.name)

    def harvest_csw_documents(self, url):
        try:
            from ckanext.csw.services import CswService
            from owslib.csw import namespaces
        except ImportError:
            self.job.report['errors'].append('No CSW support installed -- install ckanext-csw')
            raise
        csw = CswService(url)
        used_identifiers = []
        try:
            for identifier in csw.getidentifiers(page=10):
                log.info('Got identifier %s from the CSW', identifier)
                if identifier in used_identifiers:
                    log.error('CSW identifier %r already used, skipping...' % identifier)
                    continue
                if identifier is None:
                    self.job.report['errors'].append('CSW returned identifier %r, skipping...' % identifier)
                    log.error('CSW returned identifier %r, skipping...' % identifier)
                    ## log an error here? happens with the dutch data
                    continue
                used_identifiers.append(identifier)
                record = csw.getrecordbyid([identifier])
                if record is None:
                    self.job.report['errors'].append('Empty record for ID %s' % identifier)
                    log.error('Empty record for ID %s' % identifier)
                    continue
                ## we could maybe do something better here by using the
                ## parsed metadata...
                log.info('Parsing the record XML len %s', len(record['xml']))
                self.harvest_gemini_document(record['xml'])
        except Exception, e:
            self.job.report['errors'].append('Problem connecting to the CSW: %s'%e)

    def harvest_waf_documents(self, content):
        for url in self.extract_urls(content):
            try:
                content = self.get_content(url)
            except HarvesterError, error:
                msg = "Couldn't harvest WAF link: %s: %s" % (url, error)
                self.job.report['errors'].append(msg)
            else:
                if "<gmd:MD_Metadata" in content:
                    self.harvest_gemini_document(content)
        if not self.job.report['added']:
            self.job.report['errors'].append("Couldn't find any links to metadata files.")

    def extract_urls(self, content):
        """\
        Get the URLs out of a WAF index page
        """
        try:
            parser = etree.HTMLParser()
            tree = etree.fromstring(content, parser=parser)
        except Exception, inst:
            msg = "Couldn't parse content into a tree: %s: %s" \
                  % (inst, content)
            raise HarvesterError(msg)
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
        base_url = self.job.source.url
        base_url = base_url.split('/')
        if 'index' in base_url[-1]:
            base_url.pop()
        base_url = '/'.join(base_url)
        base_url.rstrip('/')
        base_url += '/'
        return [base_url + i for i in urls]

    def _create_package_from_data(self, package_data, package = None):
        ''' 
        {'extras': {'INSPIRE': 'True',
                    'bbox-east-long': '-3.12442',
                    'bbox-north-lat': '54.218407',
                    'bbox-south-lat': '54.039634',
                    'bbox-west-long': '-3.32485',
                    'constraint': 'conditions unknown; (e) intellectual property rights;',
                    'dataset-reference-date': [{'type': 'creation',
                                                'value': '2008-10-10'},
                                               {'type': 'revision',
                                                'value': '2009-10-08'}],
                    'guid': '00a743bf-cca4-4c19-a8e5-e64f7edbcadd',
                    'metadata-date': '2009-10-16',
                    'metadata-language': 'eng',
                    'published_by': 0,
                    'resource-type': 'dataset',
                    'spatial-reference-system': '<gmd:MD_ReferenceSystem xmlns:gmd="http://www.isotc211.org/2005/gmd" xmlns:gco="http://www.isotc211.org/2005/gco" xmlns:gml="http://www.opengis.net/gml/3.2" xmlns:xlink="http://www.w3.org/1999/xlink"><gmd:referenceSystemIdentifier><gmd:RS_Identifier><gmd:code><gco:CharacterString>urn:ogc:def:crs:EPSG::27700</gco:CharacterString></gmd:code></gmd:RS_Identifier></gmd:referenceSystemIdentifier></gmd:MD_ReferenceSystem>',
                    'temporal_coverage-from': '1977-03-10T11:45:30',
                    'temporal_coverage-to': '2005-01-15T09:10:00'},
         'name': 'council-owned-litter-bins',
         'notes': 'Location of Council owned litter bins within Borough.',
         'resources': [{'description': 'Resource locator',
                        'format': 'Unverified',
                        'url': 'http://www.barrowbc.gov.uk'}],
         'tags': ['Utility and governmental services'],
         'title': 'Council Owned Litter Bins'}
        '''

        if not package:
            package = model.Package()

        rev = model.repo.new_revision()
        
        relationship_attr = ['extras', 'resources', 'tags']

        package_properties = {}
        for key, value in package_data.iteritems():
            if key not in relationship_attr:
                setattr(package, key, value)

        tags = package_data.get('tags', [])

        for tag in tags:
            package.add_tag_by_name(tag, autoflush=False)
        
        for resource_dict in package_data.get("resources", []):
            resource = model.Resource(**resource_dict)
            package.resources[:] = []
            package.resources.append(resource)

        for key, value in package_data.get("extras", {}).iteritems():
            extra = model.PackageExtra(key=key, value=value)
            package._extras[key] = extra

        model.Session.add(package)
        model.Session.flush()

        model.setup_default_user_roles(package, [])

        rev.message = _(u'Harvester: Created package %s') \
                      % str(package.id)

        model.Session.add(rev)
        model.Session.commit()

        return package

