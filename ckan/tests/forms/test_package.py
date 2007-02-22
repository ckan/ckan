# needed for config to be set and db access to work
import ckan.tests

import ckan.forms
import ckan.models

class TestPackageSchema:

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
    testname = u'schematestpkg'

    def teardown_class(self):
        ckan.models.dm.packages.purge(self.testname)

    def _check_from_python(self, key):
        assert self.out[key] == self.exp[key]

    def test_from_python(self):
        print 'out', self.out
        print 'exp', self.exp
        keys = self.exp.keys()
        assert len(keys) == len(self.out.keys())
        for key in keys:
            self._check_from_python(key) 

    def test_to_python(self):
        testpkg = ckan.models.dm.packages.create(name=self.testname)
        indict = {
                'id'   : testpkg.id,
                'name' : self.testname,
                'notes': u'some new notes',
                'tags' : u'russian tolstoy',
                }
        outpkg = self.schema.to_python(indict)
        outpkg.notes == indict['notes']
        taglist = []
        for xx in outpkg.tags:
            taglist.append(xx.name)
        assert u'russian' in taglist
        assert u'tolstoy' in taglist

