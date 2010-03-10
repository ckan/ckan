from licenses.service import LicensesService2
from pylons import config 

class License(object):

    def __init__(self, data):
        self._data = data

    def __getattr__(self, name):
        return self._data[name]

    def __getitem__(self, key):
        return self._data[key]

    def isopen(self):
        return self.is_okd_compliant or self.is_osi_compliant

class LicenseRegister(object):
    """Dictionary-like interface to a group of licenses."""

    def __init__(self, group_url=''):
        group_url = config.get('licenses_group_url', group_url) 
        self.service = LicensesService2(group_url)
        entity_list = self.service.get_licenses()
        self.licenses = [License(entity) for entity in entity_list]

    def __getitem__(self, key, default=Exception):
        for license in self.licenses:
            if key == license['id']:
                return license
        if default != Exception:
            return default
        else:
            raise Exception, "License not found: %s" % key

    def keys(self):
        return [license['id'] for license in self.licenses]

    def values(self):
        return self.licenses

    def items(self):
        return [(license['id'], license) for license in self.licenses]
        
    def __iter__(self):
        return iter(self.keys())

