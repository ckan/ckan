# encoding: utf-8
from __future__ import annotations

import datetime
import re
import logging
from typing import Any, Iterator, Optional, Union, Dict

import requests

from ckan.common import config

from ckan.common import _, json

log = logging.getLogger(__name__)


class License():
    """Domain object for a license."""

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data
        for (key, value) in self._data.items():
            if key == 'date_created':
                # Parse ISO formatted datetime.
                # type_ignore_reason: typechecker can't guess number of args
                value = datetime.datetime(*list(
                    int(item) for item
                    in re.split(r'[^\d]', value)  # type: ignore
                ))
                self._data[key] = value
            elif isinstance(value, str):
                self._data[key] = value

    def __getattr__(self, name: str) -> Any:
        try:
            return self._data[name]
        except KeyError as e:
            # Python3 strictly requires `AttributeError` for correct
            # behavior of `hasattr`
            raise AttributeError(*e.args)

    def isopen(self) -> bool:
        if not hasattr(self, '_isopen'):
            self._isopen = self.od_conformance == 'approved' or \
                self.osd_conformance == 'approved'
        return self._isopen

    def license_dictize(self) -> dict[str, Any]:
        data = self._data.copy()
        if 'date_created' in data:
            value = data['date_created']
            value = value.isoformat()
            data['date_created'] = value
        return data


class LicenseRegister(object):
    """Dictionary-like interface to a group of licenses."""
    licenses: list[License]

    def __init__(self):
        group_url = config.get('licenses_group_url')
        if group_url:
            self.load_licenses(group_url)
        else:
            default_license_list: list[DefaultLicense] = [
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

    def load_licenses(self, license_url: str) -> None:

        try:
            if license_url.startswith('file://'):
                with open(license_url.replace('file://', ''), 'r') as f:
                    license_data = json.load(f)
            else:
                timeout = config.get('ckan.requests.timeout')
                response = requests.get(license_url, timeout=timeout)
                license_data = response.json()
        except requests.RequestException as e:
            msg = "Couldn't get the licenses file {}: {}".format(license_url, e)
            raise Exception(msg)
        except ValueError as e:
            msg = "Couldn't parse the licenses file {}: {}".format(license_url, e)
            raise Exception(msg)
        for license in license_data:
            if isinstance(license, str):
                license = license_data[license]
        self._create_license_list(license_data, license_url)

    def _create_license_list(
            self, license_data: Union[
                list[dict[str, Any]], dict[str, dict[str, Any]], Any],
            license_url: str=''):
        if isinstance(license_data, dict):
            self.licenses = [License(entity) for entity in license_data.values()]
        elif isinstance(license_data, list):
            self.licenses = [License(entity) for entity in license_data]
        else:
            msg = "Licenses at %s must be dictionary or list" % license_url
            raise ValueError(msg)

    def __getitem__(
            self, key: str,
            default: Any=Exception) -> Union[License, Any]:
        for license in self.licenses:
            if key == license.id:
                return license
        if default != Exception:
            return default
        else:
            raise KeyError("License not found: %s" % key)

    def get(
            self, key: str, default: Optional[Any]=None
    ) -> Union[License, Any]:
        return self.__getitem__(key, default)

    def keys(self) -> list[str]:
        return [license.id for license in self.licenses]

    def values(self) -> list[License]:
        return self.licenses

    def items(self) -> list[tuple[str, License]]:
        return [(license.id, license) for license in self.licenses]

    def __iter__(self) -> Iterator[str]:
        return iter(self.keys())

    def __len__(self) -> int:
        return len(self.licenses)


class DefaultLicense(Dict[str, Any]):
    ''' The license was a dict but this did not allow translation of the
    title.  This is a slightly changed dict that allows us to have the title
    as a property and so translated. '''

    domain_content: bool = False
    domain_data: bool = False
    domain_software: bool = False
    family: str = ''
    is_generic: bool = False
    od_conformance: str = 'not reviewed'
    osd_conformance: str = 'not reviewed'
    maintainer: str = ''
    status: str = 'active'
    url: str = ''
    id: str = ''

    @property
    def title(self) -> str:
        return ""

    _keys: list[str] = ['domain_content',
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

    def __getitem__(self, key: str) -> Any:
        ''' behave like a dict but get from attributes '''
        if key in self._keys:
            value = getattr(self, key)
            if isinstance(value, str):
                return str(value)
            else:
                return value
        else:
            raise KeyError(key)

    def copy(self) -> dict[str, Any]:
        ''' create a dict of the license used by the licenses api '''
        out: dict[str, Any] = {}
        for key in self._keys:
            out[key] = str(getattr(self, key))
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
    url = "https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/"

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
