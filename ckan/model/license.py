from pylons import config
from pylons.i18n import _
import datetime
import urllib2
from ckan.lib.helpers import json
import re

class License(object):
    """Domain object for a license."""

    def __init__(self, data):
        self._data = data
        for (key, value) in self._data.items():
            if key == 'date_created':
                # Parse ISO formatted datetime.
                value = datetime.datetime(*map(int, re.split('[^\d]', value)))
                self._data[key] = value
            elif isinstance(value, str):
                # Convert str to unicode (keeps Pylons and SQLAlchemy happy).
                value = value.decode('utf8')
                self._data[key] = value

    def __getattr__(self, name):
        return self._data[name]

    def __getitem__(self, key):
        return self._data[key]

    def isopen(self):
        return self.is_okd_compliant or self.is_osi_compliant

    def as_dict(self):
        data = self._data.copy()
        if 'date_created' in data:
            value = data['date_created']
            value = value.isoformat()
            data['date_created'] = value
        return data


class LicenseRegister(object):
    """Dictionary-like interface to a group of licenses."""

    def __init__(self):
        group_url = config.get('licenses_group_url', None)
        if group_url:
            self.load_licenses(group_url)
        else:
            default_license_list = [
                {
                    "domain_content": False, 
                    "domain_data": False, 
                    "domain_software": False, 
                    "family": "", 
                    "id": "notspecified", 
                    "is_generic": True, 
                    "is_okd_compliant": False, 
                    "is_osi_compliant": False, 
                    "maintainer": "", 
                    "status": "active", 
                    "title": _("License Not Specified"), 
                    "url": ""
                }, 
                {
                    "domain_content": False, 
                    "domain_data": True, 
                    "domain_software": False, 
                    "family": "", 
                    "id": "odc-pddl", 
                    "is_okd_compliant": True, 
                    "is_osi_compliant": False, 
                    "maintainer": "", 
                    "status": "active", 
                    "title": "Open Data Commons Public Domain Dedication and Licence (PDDL)", 
                    "url": "http://www.opendefinition.org/licenses/odc-pddl"
                }, 
                {
                    "domain_content": False, 
                    "domain_data": True, 
                    "domain_software": False, 
                    "family": "", 
                    "id": "odc-odbl", 
                    "is_okd_compliant": True, 
                    "is_osi_compliant": False, 
                    "maintainer": "", 
                    "status": "active", 
                    "title": "Open Data Commons Open Database License (ODbL)", 
                    "url": "http://www.opendefinition.org/licenses/odc-odbl"
                }, 
                {
                    "domain_content": False, 
                    "domain_data": True, 
                    "domain_software": False, 
                    "family": "", 
                    "id": "odc-by", 
                    "is_okd_compliant": True, 
                    "is_osi_compliant": False, 
                    "maintainer": "", 
                    "status": "active", 
                    "title": "Open Data Commons Attribution License", 
                    "url": "http://www.opendefinition.org/licenses/odc-by"
                }, 
                {
                    "domain_content": True, 
                    "domain_data": True, 
                    "domain_software": False, 
                    "family": "", 
                    "id": "cc-zero", 
                    "is_okd_compliant": True, 
                    "is_osi_compliant": False, 
                    "maintainer": "", 
                    "status": "active", 
                    "title": "Creative Commons CCZero", 
                    "url": "http://www.opendefinition.org/licenses/cc-zero"
                }, 
                {
                    "domain_content": True, 
                    "domain_data": False, 
                    "domain_software": False, 
                    "family": "", 
                    "id": "cc-by", 
                    "is_okd_compliant": True, 
                    "is_osi_compliant": False, 
                    "maintainer": "", 
                    "status": "active", 
                    "title": "Creative Commons Attribution", 
                    "url": "http://www.opendefinition.org/licenses/cc-by"
                }, 
                {
                    "domain_content": True, 
                    "domain_data": False, 
                    "domain_software": False, 
                    "family": "", 
                    "id": "cc-by-sa", 
                    "is_okd_compliant": True, 
                    "is_osi_compliant": False, 
                    "maintainer": "", 
                    "status": "active", 
                    "title": "Creative Commons Attribution Share-Alike", 
                    "url": "http://www.opendefinition.org/licenses/cc-by-sa"
                }, 
                {
                    "domain_content": True, 
                    "domain_data": False, 
                    "domain_software": False, 
                    "family": "", 
                    "id": "gfdl", 
                    "is_okd_compliant": True, 
                    "is_osi_compliant": False, 
                    "maintainer": "", 
                    "status": "active", 
                    "title": "GNU Free Documentation License", 
                    "url": "http://www.opendefinition.org/licenses/gfdl"
                }, 
                {
                    "domain_content": True, 
                    "domain_data": False, 
                    "domain_software": False, 
                    "family": "", 
                    "id": "other-open", 
                    "is_generic": True, 
                    "is_okd_compliant": True, 
                    "is_osi_compliant": False, 
                    "maintainer": "", 
                    "status": "active", 
                    "title": _("Other (Open)"), 
                    "url": ""
                }, 
                {
                    "domain_content": True, 
                    "domain_data": False, 
                    "domain_software": False, 
                    "family": "", 
                    "id": "other-pd", 
                    "is_generic": True, 
                    "is_okd_compliant": True, 
                    "is_osi_compliant": False, 
                    "maintainer": "", 
                    "status": "active", 
                    "title": _("Other (Public Domain)"), 
                    "url": ""
                }, 
                {
                    "domain_content": True, 
                    "domain_data": False, 
                    "domain_software": False, 
                    "family": "", 
                    "id": "other-at", 
                    "is_generic": True, 
                    "is_okd_compliant": True, 
                    "is_osi_compliant": False, 
                    "maintainer": "", 
                    "status": "active", 
                    "title": _("Other (Attribution)"), 
                    "url": ""
                }, 
                {
                    "domain_content": True, 
                    "domain_data": False, 
                    "domain_software": False, 
                    "family": "", 
                    "id": "uk-ogl", 
                    "is_okd_compliant": True, 
                    "is_osi_compliant": False, 
                    "maintainer": "", 
                    "status": "active", 
                    "title": "UK Open Government Licence (OGL)", 
                    "url": "http://reference.data.gov.uk/id/open-government-licence"
                }, 
                {
                    "domain_content": False, 
                    "domain_data": False, 
                    "domain_software": False, 
                    "family": "", 
                    "id": "cc-nc", 
                    "is_okd_compliant": False, 
                    "is_osi_compliant": False, 
                    "maintainer": "", 
                    "status": "active", 
                    "title": "Creative Commons Non-Commercial (Any)", 
                    "url": "http://creativecommons.org/licenses/by-nc/2.0/"
                }, 
                {
                    "domain_content": False, 
                    "domain_data": False, 
                    "domain_software": False, 
                    "family": "", 
                    "id": "other-nc", 
                    "is_generic": True, 
                    "is_okd_compliant": False, 
                    "is_osi_compliant": False, 
                    "maintainer": "", 
                    "status": "active", 
                    "title": _("Other (Non-Commercial)"), 
                    "url": ""
                }, 
                {
                    "domain_content": False, 
                    "domain_data": False, 
                    "domain_software": False, 
                    "family": "", 
                    "id": "other-closed", 
                    "is_generic": True, 
                    "is_okd_compliant": False, 
                    "is_osi_compliant": False, 
                    "maintainer": "", 
                    "status": "active", 
                    "title": _("Other (Not Open)"), 
                    "url": ""
                }
                ]
            self._create_license_list(default_license_list)

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
        self._create_license_list(license_data)

    def _create_license_list(self, license_data):
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
