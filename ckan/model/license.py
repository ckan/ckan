import datetime
import urllib2
import re

from pylons import config
from ckan.common import _, json
from sqlalchemy import types, Column, Table

import logging
log = logging.getLogger('ckan.logic')

import meta
import domain_object
import types as _types

CORE_RESOURCE_COLUMNS = ['id', 'title', 'is_okd_compliant', 'is_generic', 'url',
                         'home_url', 'status']

license_statuses = set(['active', 'deleted']) # "active" and "deleted" statuses should never be removed
license_table = Table('license', meta.metadata,
        Column('id', types.UnicodeText, primary_key=True),
        Column('title', types.UnicodeText, nullable=False),
        Column('is_okd_compliant', types.Boolean, default=False),
        Column('is_generic', types.Boolean, default=False),
        Column('url', types.UnicodeText),
        Column('home_url', types.UnicodeText),
        Column('extras', _types.JsonDictType),
        Column('status', types.Enum(*license_statuses, name='license_status'), nullable=False),
        )


class License(domain_object.DomainObject):
    """Domain object for a license."""
    def __init__(self, data={}, extras=None):
        self.extras = extras or {}
        domain_object.DomainObject.__init__(self, **data)

    def isopen(self):
        return self.is_okd_compliant or (hasattr(self, 'is_osi_compliant') and self.is_osi_compliant)

    def __getitem__(self, item):
        return self.as_dict().get(item)

    def as_dict(self):
        data = self.__dict__
        default_license = DefaultLicense()
        for k in data.keys():
            try:
                getattr(default_license, k)
            except (KeyError, AttributeError):
                del data[k]
        for (key, value) in data.items():
            if key == 'date_created':
                # Parse ISO formatted datetime.
                value = datetime.datetime(*map(int, re.split('[^\d]', value)))
                data[key] = value.isoformat()
            elif isinstance(value, str):
                # Convert str to unicode (keeps Pylons and SQLAlchemy happy).
                value = value.decode('utf8')
                data[key] = value
        if isinstance(data.get('extras'), dict):
            for k, v in data['extras'].items():
                data[k] = v
            del data['extras']
        return data


class LicenseRegister(object):
    """Dictionary-like interface to a group of licenses."""

    def __init__(self, statuses=('active',)):
        group_url = config.get('licenses_group_url', None)
        if group_url:
            self.load_licenses(group_url)
        else:
            self.load_licenses_from_db(statuses)

    def load_licenses_from_db(self, statuses):
        self.licenses = meta.Session.query(License).filter(License.status.in_(statuses)).all()

    # DEPRECATED
    def get_default_license_list(self):
        default_license_list = [
            LicenseNotSpecified().copy(),
            LicenseOpenDataCommonsPDDL().copy(),
            LicenseOpenDataCommonsOpenDatabase().copy(),
            LicenseOpenDataAttribution().copy(),
            LicenseCreativeCommonsZero().copy(),
            LicenseCreativeCommonsAttribution().copy(),
            LicenseCreativeCommonsAttributionShareAlike().copy(),
            LicenseGNUFreeDocument().copy(),
            LicenseOtherOpen().copy(),
            LicenseOtherPublicDomain().copy(),
            LicenseOtherAttribution().copy(),
            LicenseOpenGovernment().copy(),
            LicenseCreativeCommonsNonCommercial().copy(),
            LicenseOtherNonCommercial().copy(),
            LicenseOtherClosed().copy(),
            ]
        self._create_license_list(default_license_list)
        return self

    def load_licenses(self, license_url):
        try:
            response = urllib2.urlopen(license_url)
            response_body = response.read()
        except Exception, inst:
            msg = "Couldn't connect to licenses service %r: %s" % (license_url, inst)
            raise Exception, msg
        try:
            license_data = json.loads(response_body)
        except Exception, inst:
            msg = "Couldn't read response from licenses service %r: %s" % (response_body, inst)
            raise Exception, inst
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
            raise KeyError, "License not found: %s" % key

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
    family = ""
    is_generic = False
    is_okd_compliant = False
    is_osi_compliant = False
    maintainer = ""
    status = "active"
    url = ""
    home_url = ""
    title = ''
    extras = {}
    id = ''

    keys = ['domain_content',
            'id',
            'domain_data',
            'domain_software',
            'family',
            'is_generic',
            'is_okd_compliant',
            'is_osi_compliant',
            'maintainer',
            'status',
            'url',
            'home_url',
            'extras',
            'title']

    def __getitem__(self, key):
        ''' behave like a dict but get from attributes '''
        if key in self.keys:
            value = getattr(self, key)
            if isinstance(value, str):
                return unicode(value)
            else:
                return value
        else:
            raise KeyError()

    def copy(self):
        ''' create a dict of the license used by the licenses api '''
        out = {}
        for key in self.keys:
            out[key] = unicode(getattr(self, key))
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
    is_okd_compliant = True
    url = "http://www.opendefinition.org/licenses/odc-pddl"

    @property
    def title(self):
        return _("Open Data Commons Public Domain Dedication and License (PDDL)")

class LicenseOpenDataCommonsOpenDatabase(DefaultLicense):
    domain_data = True
    id = "odc-odbl"
    is_okd_compliant = True
    url = "http://www.opendefinition.org/licenses/odc-odbl"

    @property
    def title(self):
        return _("Open Data Commons Open Database License (ODbL)")

class LicenseOpenDataAttribution(DefaultLicense):
    domain_data = True
    id = "odc-by"
    is_okd_compliant = True
    url = "http://www.opendefinition.org/licenses/odc-by"

    @property
    def title(self):
        return _("Open Data Commons Attribution License")

class LicenseCreativeCommonsZero(DefaultLicense):
    domain_content = True
    domain_data = True
    id = "cc-zero"
    is_okd_compliant = True
    url = "http://www.opendefinition.org/licenses/cc-zero"

    @property
    def title(self):
        return _("Creative Commons CCZero")

class LicenseCreativeCommonsAttribution(DefaultLicense):
    id = "cc-by"
    is_okd_compliant = True
    url = "http://www.opendefinition.org/licenses/cc-by"

    @property
    def title(self):
        return _("Creative Commons Attribution")

class LicenseCreativeCommonsAttributionShareAlike(DefaultLicense):
    domain_content = True
    id = "cc-by-sa"
    is_okd_compliant = True
    url = "http://www.opendefinition.org/licenses/cc-by-sa"

    @property
    def title(self):
        return _("Creative Commons Attribution Share-Alike")

class LicenseGNUFreeDocument(DefaultLicense):
    domain_content = True
    id = "gfdl"
    is_okd_compliant = True
    url = "http://www.opendefinition.org/licenses/gfdl"
    @property
    def title(self):
        return _("GNU Free Documentation License")

class LicenseOtherOpen(DefaultLicense):
    domain_content = True
    id = "other-open"
    is_generic = True
    is_okd_compliant = True

    @property
    def title(self):
        return _("Other (Open)")

class LicenseOtherPublicDomain(DefaultLicense):
    domain_content = True
    id = "other-pd"
    is_generic = True
    is_okd_compliant = True

    @property
    def title(self):
        return _("Other (Public Domain)")

class LicenseOtherAttribution(DefaultLicense):
    domain_content = True
    id = "other-at"
    is_generic = True
    is_okd_compliant = True

    @property
    def title(self):
        return _("Other (Attribution)")

class LicenseOpenGovernment(DefaultLicense):
    domain_content = True
    id = "uk-ogl"
    is_okd_compliant = True
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

meta.mapper(License, license_table)
