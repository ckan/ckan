import urllib2
import logging
from lxml import etree

from pylons.i18n import _

from ckan.lib.base import *
from ckan.lib.cache import proxy_cache
from ckan.lib.package_saver import PackageSaver, ValidationException
from ckan.lib.package_saver import WritePackageFromBoundFieldset
from ckan.lib.base import BaseController
from ckan.plugins import PluginImplementations, IPackageController
from ckan.model.harvesting import HarvesterError, HarvesterUrlError
from ckan.model.harvesting import GeminiDocument
from ckan.model.harvesting import HarvestedDocument
import ckan.forms
from ckan.forms import GetPackageFieldset
from ckan.forms import GetEditFieldsetPackageData
import ckan.model as model
import ckan.authz
import ckan.rating
import ckan.misc
from ckan.lib.cswclient import CswClient
from ckan.lib.cswclient import CswError

logger = logging.getLogger('ckan.controllers')


def decode_response(resp):
    """Decode a response to unicode
    """
    encoding = resp.headers['content-type'].split('charset=')[-1]
    content = resp.read()
    try:
        data = unicode(content, encoding)
    except LookupError:
        data = unicode(content, 'utf8')  # XXX is this a fair assumption?
    return data


class HarvestingSourceController(BaseController):
    pass


class ExampleController(BaseController):
    authorizer = ckan.authz.Authorizer()
    extensions = PluginImplementations(IPackageController)

    # XXX examples
    def search(self):
        c.q = request.params.get('q')  # unicode format (decoded from utf8)
        return render('package/search.html')

    @proxy_cache()
    def read(self, id):
        # is the user allowed to see this package?
        auth_for_read = self.authorizer.am_authorized(c,
                                                      model.Action.READ,
                                                      c.pkg)
        if not auth_for_read:
            abort(401, str(gettext('Unauthorized to read package %s') % id))
        PackageSaver().render_package(c.pkg)
        return render('package/read.html')


class HarvestingJobController(object):
    def __init__(self, job):
        self.job = job

     def harvest_documents(self):
         self.job.start_report()
         try:
             try:
                 content = self.get_content(self.job.source.url)
             except HarvesterUrlError, exception:
                 msg = "Error harvesting source: %s" % exception
                 self.job.report_error(msg)
             else:
                 source_type = self.detect_source_type(content)
                 if source_type == None:
                     self.job.report_error(
                         "Unable to detect source type from content")
                 elif source_type == 'doc':
                     self.harvest_gemini_document(content)
                 elif source_type == 'csw':
                     self.harvest_csw_documents(url=self.job.source.url)
                 elif source_type == 'waf':
                     self.harvest_waf_documents(content)
                 else:
                     raise HarvesterError(
                         "Source type '%s' not supported" % source_type)
         except Exception, e:
             self.job.report_error("Harvesting system error: %r" % e)
             self.job.save()
             raise
         else:
             if not self.job.report_has_errors():
                 self.job.set_status_success()
         self.job.save()
         return self.job

    def write_package_from_gemini_string(self, content):
        """Create or update a Package based on some content that has
        come from a URL.

        Also store the raw content as a HarvestedDocument (with
        references to its source and its package)
        """
        # Look for previously harvested document matching Gemini GUID
        gemini_document = GeminiDocument(content)
        gemini_values = gemini_document.read_values()
        gemini_guid = gemini_values['guid']
        harvested_documents = HarvestedDocument.filter(guid=gemini_guid).all()
        if len(harvested_documents) > 1:
            # A programming error; should never happen
            raise Exception(
                "More than one harvested document GUID %s" % gemini_guid)
        elif len(harvested_documents) == 1:
             # we've previously harvested this (i.e. it's an update)
            harvested_doc = harvested_documents[0]
            if harvested_doc.source.id != self.job.source.id:
                # A 'user' error: there are two or more sources
                # pointing to the same harvested document
                raise HarvesterError(
                    "Another source is using metadata GUID %s" % \
                                    self.job.source.id)
            if harvested_doc.read_values() == gemini_values:
                # nothing's changed
                return None
            package = harvested_doc.package
        else:
            harvested_doc = None
            package = None
        package_data = {
            'name': gemini_values['guid'],
            'title': gemini_values['title'],
            'extras': gemini_values,
        }
        if package == None:
            # Create new package from data.
            package = self._create_package_from_data(package_data)
        else:
            package = self._update_package_from_data(package, package_data)
        harvested_doc = HarvestedDocument(content=content,
                                          guid=gemini_guid,
                                          package=package,
                                          source=self.job.source)
        harvested_doc.save()
        return package

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

    def harvest_gemini_document(self, gemini_string):
        try:
            self.validate_document(gemini_string)
        except Exception, exception:
            msg = "Error validating harvested content: %s" % exception
            self.job.report_error(msg)
        else:
            try:
                package = self.write_package_from_gemini_string(gemini_string)
            except HarvesterError, exception:
                msg = "%s" % exception
                self.job.report_error(msg)
            except Exception, exception:
                msg = ("System error writing package from harvested"
                       "content: %s" % exception)
                self.job.report_error(msg)
                raise
            else:
                if package:
                    self.job.report_package(package.id)

    def harvest_csw_documents(self, url):
        try:
            csw_client = CswClient(base_url=url)
            records = csw_client.get_records()
        except CswError, error:
            msg = "Couldn't get records from CSW: %s: %s" % (url, error)
            self.job.report_error(msg)
        for gemini_string in records:
            self.harvest_gemini_document(gemini_string)

    def harvest_waf_documents(self, content):
        for url in self.extract_urls(content):
            try:
                content = self.get_content(url)
            except HarvesterError, error:
                msg = "Couldn't harvest WAF link: %s: %s" % (url, error)
                self.job.report_error(msg)
            else:
                if "<gmd:MD_Metadata" in content:
                    self.harvest_gemini_document(content)
        if not self.job.get_report()['packages']:
            self.job.report_error("Couldn't find any links to metadata files.")

    def extract_urls(self, content):
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

    def validate_document(self, content):
        pass

    def _create_package_from_data(self, package_data):
        user_editable_groups = []
        # mock up a form so we can validate data
        fs = ckan.forms.get_standard_fieldset(
            user_editable_groups=user_editable_groups)
        try:
            fa_dict = ckan.forms.edit_package_dict(
                ckan.forms.get_package_dict(
                    fs=fs,
                    user_editable_groups=user_editable_groups),
                package_data)
        except ckan.forms.PackageDictFormatError, exception:
            msg = 'Package format incorrect: %r' % exception
            raise Exception(msg)
        fs = fs.bind(model.Package,
                     data=fa_dict,
                     session=model.Session)
        # Validate the fieldset.
        is_valid = fs.validate()
        if is_valid:
            rev = model.repo.new_revision()
            #rev.author = self.rest_api_user
            rev.message = _(u'Harvester: Created package %s') \
                          % str(fs.model.id)
            # Construct catalogue entity.
            fs.sync()
            # Construct access control entities.
            #if self.rest_api_user:
            #    admins = [model.User.by_name(
            #               self.rest_api_user.decode('utf8'))]
            #else:
            #    admins = []
            # Todo: Better 'admins' than this?
            admins = []
            package = fs.model
            model.setup_default_user_roles(package, admins)
            model.repo.commit()
        else:
            # Complain about validation errors.
            msg = 'Validation error:'
            errors = fs.errors.items()
            for error in errors:
                attr_name = error[0].name
                error_msg = error[1][0]
                msg += ' %s: %s' % (attr_name.capitalize(), error_msg)
            raise HarvesterError(msg)
        return package

    def _update_package_from_data(self, package, package_data):
        fieldset = GetPackageFieldset().fieldset
        fieldset_data = GetEditFieldsetPackageData(
            fieldset=fieldset, package=package, data=package_data).data
        bound_fieldset = fieldset.bind(package, data=fieldset_data)
        log_message = u'harvester'
        author = u''
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
            raise HarvesterError(msg)
        return package
