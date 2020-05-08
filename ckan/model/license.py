# encoding: utf-8

import datetime
import re

import requests

from ckan.common import config
from ckan.common import asbool
import six
from six import text_type, string_types

from ckan.common import _, json
import ckan.lib.maintain as maintain

log = __import__('logging').getLogger(__name__)


class License(object):
    """Domain object for a license."""

    def __init__(self, data):
        # convert old keys if necessary
        if 'is_okd_compliant' in data:
            data['od_conformance'] = 'approved' \
                if asbool(data['is_okd_compliant']) else ''
            del data['is_okd_compliant']
        if 'is_osi_compliant' in data:
            data['osd_conformance'] = 'approved' \
                if asbool(data['is_osi_compliant']) else ''
            del data['is_osi_compliant']

        self._data = data
        for (key, value) in self._data.items():
            if key == 'date_created':
                # Parse ISO formatted datetime.
                value = datetime.datetime(
                    *list(int(item) for item in re.split(r'[^\d]', value)))
                self._data[key] = value
            elif isinstance(value, str):
                if six.PY2:
                    # Convert str to unicode
                    # (keeps Pylons and SQLAlchemy happy).
                    value = six.ensure_text(value)
                self._data[key] = value

    def __getattr__(self, name):
        if name == 'is_okd_compliant':
            log.warn('license.is_okd_compliant is deprecated - use '
                     'od_conformance instead.')
            return self._data['od_conformance'] == 'approved'
        if name == 'is_osi_compliant':
            log.warn('license.is_osi_compliant is deprecated - use '
                     'osd_conformance instead.')
            return self._data['osd_conformance'] == 'approved'
        try:
            return self._data[name]
        except KeyError as e:
            # Python3 strictly requires `AttributeError` for correct
            # behavior of `hasattr`
            raise AttributeError(*e.args)

    @maintain.deprecated("License.__getitem__() is deprecated and will be "
                         "removed in a future version of CKAN. Instead, "
                         "please use attribute access.")
    def __getitem__(self, key):
        '''NB This method is deprecated and will be removed in a future version
        of CKAN. Instead, please use attribute access.
        '''
        return self.__getattr__(key)

    def isopen(self):
        if not hasattr(self, '_isopen'):
            self._isopen = self.od_conformance == 'approved' or \
                self.osd_conformance == 'approved'
        return self._isopen

    @maintain.deprecated("License.as_dict() is deprecated and will be "
                         "removed in a future version of CKAN. Instead, "
                         "please use attribute access.")
    def as_dict(self):
        '''NB This method is deprecated and will be removed in a future version
        of CKAN. Instead, please use attribute access.
        '''
        data = self._data.copy()
        if 'date_created' in data:
            value = data['date_created']
            value = value.isoformat()
            data['date_created'] = value

        # deprecated keys
        if 'od_conformance' in data:
            data['is_okd_compliant'] = data['od_conformance'] == 'approved'
        if 'osd_conformance' in data:
            data['is_osi_compliant'] = data['osd_conformance'] == 'approved'

        return data


class LicenseRegister(object):
    """Dictionary-like interface to a group of licenses."""

    def __init__(self):
        group_url = config.get('licenses_group_url', None)
        if group_url:
            self.load_licenses(group_url)
        else:
            default_license_list = [
                LicenseNotSpecified(),
                LicenseOpenDataCommonsPDDL(),
                LicenseOpenDataCommonsOpenDatabase(),
                LicenseOpenDataAttribution(),
                LicenseCreativeCommonsZero(),
                LicenseCreativeCommonsAttribution(),
                LicenseCreativeCommonsAttributionShareAlike(),
                LicenseGNUFreeDocument(),
                LicenseOtherOpen(),
                LicenseOtherPublicDomain(),
                LicenseOtherAttribution(),
                LicenseOpenGovernment(),
                LicenseCreativeCommonsNonCommercial(),
                LicenseOtherNonCommercial(),
                LicenseOtherClosed(),
                ]
            self._create_license_list(default_license_list)

    def load_licenses(self, license_url):
        try:
            if license_url.startswith('file://'):
                with open(license_url.replace('file://', ''), 'r') as f:
                    license_data = json.load(f)
            else:
                response = requests.get(license_url)
                license_data = response.json()
        except requests.RequestException as e:
            msg = "Couldn't get the licenses file {}: {}".format(license_url, e)
            raise Exception(msg)
        except ValueError as e:
            msg = "Couldn't parse the licenses file {}: {}".format(license_url, e)
            raise Exception(msg)
        for license in license_data:
            if isinstance(license, string_types):
                license = license_data[license]
            if license.get('title'):
                license['title'] = _(license['title'])
        self._create_license_list(license_data, license_url)

    def _create_license_list(self, license_data, license_url=''):
        if isinstance(license_data, dict):
            self.licenses = [License(entity) for entity in license_data.values()]
        elif isinstance(license_data, list):
            self.licenses = [License(entity) for entity in license_data]
        else:
            msg = "Licenses at %s must be dictionary or list" % license_url
            raise ValueError(msg)

    def __getitem__(self, key, default=Exception):
        for license in self.licenses:
            if key == license.id:
                return license
        if default != Exception:
            return default
        else:
            raise KeyError("License not found: %s" % key)

    def get(self, key, default=None):
        return self.__getitem__(key, default=default)

    def keys(self):
        return [license.id for license in self.licenses]

    def values(self):
        return self.licenses

    def items(self):
        return [(license.id, license) for license in self.licenses]

    def __iter__(self):
        return iter(self.keys())

    def __len__(self):
        return len(self.licenses)


class DefaultLicense(dict):
    ''' The license was a dict but this did not allow translation of the
    title.  This is a slightly changed dict that allows us to have the title
    as a property and so translated. '''

    domain_content = False
    domain_data = False
    domain_software = False
    family = ''
    is_generic = False
    od_conformance = 'not reviewed'
    osd_conformance = 'not reviewed'
    maintainer = ''
    status = 'active'
    url = ''
    title = ''
    id = ''

    keys = ['domain_content',
            'id',
            'domain_data',
            'domain_software',
            'family',
            'is_generic',
            'od_conformance',
            'osd_conformance',
            'maintainer',
            'status',
            'url',
            'title']

    def __getitem__(self, key):
        ''' behave like a dict but get from attributes '''
        if key in self.keys:
            value = getattr(self, key)
            if isinstance(value, str):
                return text_type(value)
            else:
                return value
        else:
            raise KeyError(key)

    def copy(self):
        ''' create a dict of the license used by the licenses api '''
        out = {}
        for key in self.keys:
            out[key] = text_type(getattr(self, key))
        return out

class LicenseNotSpecified(DefaultLicense):
    id = "notspecified"
    is_generic = True

    @property
    def title(self):
        return _("License not specified")

class LicenseOpenDataCommonsPDDL(DefaultLicense):
    domain_data = True
    id = "odc-pddl"
    od_conformance = 'approved'
    url = "http://www.opendefinition.org/licenses/odc-pddl"

    @property
    def title(self):
        return _("Open Data Commons Public Domain Dedication and License (PDDL)")

class LicenseOpenDataCommonsOpenDatabase(DefaultLicense):
    domain_data = True
    id = "odc-odbl"
    od_conformance = 'approved'
    url = "http://www.opendefinition.org/licenses/odc-odbl"

    @property
    def title(self):
        return _("Open Data Commons Open Database License (ODbL)")

class LicenseOpenDataAttribution(DefaultLicense):
    domain_data = True
    id = "odc-by"
    od_conformance = 'approved'
    url = "http://www.opendefinition.org/licenses/odc-by"

    @property
    def title(self):
        return _("Open Data Commons Attribution License")

class LicenseCreativeCommonsZero(DefaultLicense):
    domain_content = True
    domain_data = True
    id = "cc-zero"
    od_conformance = 'approved'
    url = "http://www.opendefinition.org/licenses/cc-zero"

    @property
    def title(self):
        return _("Creative Commons CCZero")

class LicenseCreativeCommonsAttribution(DefaultLicense):
    id = "cc-by"
    od_conformance = 'approved'
    url = "http://www.opendefinition.org/licenses/cc-by"

    @property
    def title(self):
        return _("Creative Commons Attribution")

class LicenseCreativeCommonsAttributionShareAlike(DefaultLicense):
    domain_content = True
    id = "cc-by-sa"
    od_conformance = 'approved'
    url = "http://www.opendefinition.org/licenses/cc-by-sa"

    @property
    def title(self):
        return _("Creative Commons Attribution Share-Alike")

class LicenseGNUFreeDocument(DefaultLicense):
    domain_content = True
    id = "gfdl"
    od_conformance = 'approved'
    url = "http://www.opendefinition.org/licenses/gfdl"
    @property
    def title(self):
        return _("GNU Free Documentation License")

class LicenseOtherOpen(DefaultLicense):
    domain_content = True
    id = "other-open"
    is_generic = True
    od_conformance = 'approved'

    @property
    def title(self):
        return _("Other (Open)")

class LicenseOtherPublicDomain(DefaultLicense):
    domain_content = True
    id = "other-pd"
    is_generic = True
    od_conformance = 'approved'

    @property
    def title(self):
        return _("Other (Public Domain)")

class LicenseOtherAttribution(DefaultLicense):
    domain_content = True
    id = "other-at"
    is_generic = True
    od_conformance = 'approved'

    @property
    def title(self):
        return _("Other (Attribution)")

class LicenseOpenGovernment(DefaultLicense):
    domain_content = True
    id = "uk-ogl"
    od_conformance = 'approved'
    # CS: bad_spelling ignore
    url = "http://reference.data.gov.uk/id/open-government-licence"

    @property
    def title(self):
        # CS: bad_spelling ignore
        return _("UK Open Government Licence (OGL)")

class LicenseCreativeCommonsNonCommercial(DefaultLicense):
    id = "cc-nc"
    url = "http://creativecommons.org/licenses/by-nc/2.0/"

    @property
    def title(self):
        return _("Creative Commons Non-Commercial (Any)")

class LicenseOtherNonCommercial(DefaultLicense):
    id = "other-nc"
    is_generic = True

    @property
    def title(self):
        return _("Other (Non-Commercial)")

class LicenseOtherClosed(DefaultLicense):
    id = "other-closed"
    is_generic = True

    @property
    def title(self):
        return _("Other (Not Open)")
