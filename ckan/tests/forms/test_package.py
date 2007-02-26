import py.test
import formencode

# needed for config to be set and db access to work
import ckan.tests

import ckan.forms
import ckan.models

class TestPackageName:

    unique = ckan.forms.UniquePackageName()
    lower = ckan.forms.LowerCase()
    schema = ckan.forms.PackageNameSchema()
    bad_names = [ 'blAh', 'a', 'annakarenina' ]
    good_names = [ 'blah', 'ab', 'ab1', 'some-random-made-up-name' ]

    def _check_raises(self, fn, name):
        py.test.raises(formencode.Invalid, fn, name)

    def test_unique_username(self):
        self._check_raises(self.unique.to_python, self.bad_names[-1])

    def test_unique_username_ok(self):
        self.unique.to_python(self.good_names[-1])

    def test_lower_case_raises(self):
        self._check_raises(self.lower.to_python, self.bad_names[0])

    def test_lower_case_ok(self):
        self.lower.to_python(self.good_names[0])

    def test_package_name_bad(self):
        for name in self.bad_names:
            yield self._check_raises, self.schema.to_python, {'name': name}

    def test_package_name_2(self):
        for name in self.good_names:
            indict = { 'name' : name, 'id' : 10 } 
            self.schema.to_python(indict)


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

    def setup_class(self):
        self.schema = ckan.forms.PackageSchema()
        self.testname = u'schematestpkg'
        self.testname2 = u'schematestpkg2'
        self.testpkg = ckan.models.dm.packages.create(name=self.testname)
        self.indict = {
                # do not need id as name should be enough
                # 'id'   : testpkg.id,
                'name' : self.testname,
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

