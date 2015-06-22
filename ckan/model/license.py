import datetime
import urllib2
import re
import os

from pylons import config
from paste.deploy.converters import asbool

from ckan.common import json
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
                value = datetime.datetime(*map(int, re.split('[^\d]', value)))
                self._data[key] = value
            elif isinstance(value, str):
                # Convert str to unicode (keeps Pylons and SQLAlchemy happy).
                value = value.decode('utf8')
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
        return self._data[name]

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

    def as_dict(self):
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
        filepath = config.get('ckan.licenses_file')
        url = config.get('ckan.licenses_url') or \
            config.get('licenses_group_url')
        if filepath:
            self.load_licenses_from_file(filepath)
        elif url:
            self.load_licenses_from_url(url)
        else:
            default_filepath = os.path.abspath(
                os.path.join(os.path.dirname(__file__),
                             '..', 'config',
                             'licenses_default.json'))
            self.load_licenses_from_file(default_filepath)

    def load_licenses_from_file(self, filepath):
        try:
            with open(filepath, 'rb') as f:
                content = f.read()
        except IOError, inst:
            msg = "Couldn't open license file %r: %s" % (filepath, inst)
            raise Exception(msg)
        try:
            license_data = json.loads(content)
        except ValueError, inst:
            msg = "Couldn't read JSON in license file %r: %s" % (filepath, inst)
            raise Exception(msg)
        self._create_license_list(license_data, filepath)

    def load_licenses_from_url(self, license_url):
        try:
            response = urllib2.urlopen(license_url)
            response_body = response.read()
        except Exception, inst:
            msg = "Couldn't connect to licenses service %r: %s" % (license_url, inst)
            raise Exception(msg)
        try:
            license_data = json.loads(response_body)
        except Exception, inst:
            msg = "Couldn't read response from licenses service %r: %s" % (response_body, inst)
            raise Exception(inst)
        self._create_license_list(license_data, license_url)

    def _create_license_list(self, license_data, location=''):
        if isinstance(license_data, dict):
            self.licenses = [License(entity)
                             for entity in license_data.values()
                             if entity.keys() != ['comment']]
        elif isinstance(license_data, list):
            self.licenses = [License(entity) for entity in license_data
                             if entity.keys() != ['comment']]
        else:
            msg = "Licenses at %s must be a list or dictionary" % location
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

