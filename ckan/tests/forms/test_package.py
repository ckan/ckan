# needed for config to be set and db access to work
import ckan.tests

import ckan.forms
import ckan.models

class TestPackageSchemaFromPython:

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
            'licenses': [ 'OKD Compliant::Other' ] 
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

class TestPackageSchemaToPython:

    schema = ckan.forms.PackageSchema()
    testname = u'schematestpkg'
    testname2 = u'schematestpkg2'
    testpkg = ckan.models.dm.packages.create(name=testname)
    indict = {
            # do not need id as name should be enough
            # 'id'   : testpkg.id,
            'name' : testname,
            'notes': u'some new notes',
            'tags' : u'russian tolstoy',
            'licenses': [ 'OKD Compliant::Other' ] 
            }

    def teardown_class(self):
        ckan.models.dm.packages.purge(self.testname)
        ckan.models.dm.packages.purge(self.testname2)

    def test_to_python(self):
        outpkg = self.schema.to_python(self.indict)
        outpkg.notes == self.indict['notes']

    def test_to_python_tags(self):
        outpkg = self.schema.to_python(self.indict)
        taglist = []
        for xx in outpkg.tags:
            taglist.append(xx.name)
        assert u'russian' in taglist
        assert u'tolstoy' in taglist

    def test_to_python_licenses(self):
        outpkg = self.schema.to_python(self.indict)
        out = [ license.name for license in outpkg.licenses ]
        assert self.indict['licenses'] == out

    # TODO: test when we delete a tag from list ...
    def test_to_python_tags_2(self):
        testpkg2 = ckan.models.dm.packages.create(name=self.testname2)
        testpkg2.add_tag_by_name('russian')
        indict2 = {
                'name' : self.testname2,
                'tags' : u'tolstoy',
                }
        outpkg = self.schema.to_python(indict2)
        taglist = []
        for xx in outpkg.tags:
            taglist.append(xx.name)
        assert u'russian' not in taglist
        assert u'tolstoy' in taglist

