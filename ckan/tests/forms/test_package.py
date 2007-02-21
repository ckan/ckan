# needed for config to be set and db access to work
import ckan.tests

import ckan.forms
import ckan.models

class TestPackageSchema:

    # four basic operations
    # 1. to_python(dict)
    # 2. from_python(pkg)
    schema = ckan.forms.PackageSchema()
    name = 'annakarenina'
    pkg = ckan.models.dm.packages.get(name)
    out = schema.from_python(pkg)
    exp = {
            'url'     : u'http://www.annakarenina.com',
            'notes'   : u'Some test notes',
            'stateID' : None,
            'id'      : 1,
            'name'    : u'annakarenina',
            'tags'    : u'russian tolstoy',
            }

    def _check_from_python(self, key):
        assert self.out[key] == self.exp[key]

    def test_from_python(self):
        print 'out', self.out
        print 'exp', self.exp
        keys = self.exp.keys()
        assert len(keys) == len(self.out.keys())
        for key in keys:
            self._check_from_python(key) 

