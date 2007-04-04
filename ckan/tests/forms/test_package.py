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

    def test_lower_case_raises(self):
        self._check_raises(self.lower.to_python, self.bad_names[0])

    def test_lower_case_ok(self):
        self.lower.to_python(self.good_names[0])

    def test_unique_username(self):
        self._check_raises(self.unique.to_python, self.bad_names[-1])

    def test_unique_username_ok(self):
        self.unique.to_python(self.good_names[-1])

    def test_package_name_bad(self):
        for name in self.bad_names:
            yield self._check_raises, self.schema.to_python, {'name': name}

    def test_package_name_2(self):
        for name in self.good_names:
            indict = { 'name' : name, 'id' : 10 } 
            self.schema.to_python(indict)


class TestPackageSchemaFromPython:

    def setup_class(self):
        self.schema = ckan.forms.PackageSchema()
        self.name = 'annakarenina'
        rev = ckan.models.repo.youngest_revision()
        self.pkg = rev.model.packages.get(self.name)
        self.out = self.schema.from_python(self.pkg)
        active = ckan.models.State.byName('active')
        self.exp = {
                'url'     : u'http://www.annakarenina.com',
                'notes'   : u'''Some test notes

### A 3rd level heading

**Some bolded text.**

*Some italicized text.*
''',
                'state'   : active,
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
        txn = ckan.models.repo.begin_transaction()
        self.schema = ckan.forms.PackageSchema()
        self.testname = u'schematestpkg'
        self.testname2 = u'schematestpkg2'
        self.newtagname = u'schematesttag'
        self.indict = {
                # do not need id as name should be enough
                # 'id'   : testpkg.id,
                'name' : self.testname,
                'notes': u'some new notes',
                'tags' : u'russian tolstoy ' + self.newtagname,
                'licenses': [ 'OKD Compliant::Other' ] 
                }
        try: # wrap this so that teardown still gets called if there is an error
            self.testpkg = txn.model.packages.create(name=self.testname)
            self.schema.to_python(self.indict, state=txn)
            txn.commit()
        except Exception, inst:
            rev = ckan.models.repo.youngest_revision()
            try: rev.model.packages.purge(self.testname)
            except: pass
            raise
        rev = ckan.models.repo.youngest_revision()
        self.outpkg = rev.model.packages.get(self.testname)

    def teardown_class(self):
        rev = ckan.models.repo.youngest_revision()
        try: rev.model.packages.purge(self.testname)
        except: pass
        try:
            rev.model.tags.purge(self.newtagname)
        except: pass

    def test_to_python(self):
        self.outpkg.notes == self.indict['notes']

    def test_to_python_tags(self):
        taglist = []
        for xx in self.outpkg.tags:
            taglist.append(xx.tag.name)
        assert u'russian' in taglist
        assert u'tolstoy' in taglist
        assert self.newtagname in taglist

    def test_to_python_licenses(self):
        out = [ self.outpkg.license.name ]
        assert self.indict['licenses'] == out

class TestPackageSchemaToPython2:

    def setup_class(self):
        txn = ckan.models.repo.begin_transaction()
        self.schema = ckan.forms.PackageSchema()
        self.testname2 = u'schematestpkg2'
        try:
            testpkg2 = txn.model.packages.create(name=self.testname2)
            testpkg2.add_tag_by_name('russian')
            testpkg2.add_tag_by_name('tolstoy')
            indict2 = {
                    'name' : self.testname2,
                    'tags' : u'tolstoy',
                    }
            self.schema.to_python(indict2, state=txn)
            txn.commit()
        except:
            rev = ckan.models.repo.youngest_revision()
            try: rev.model.packages.purge(self.testname2)
            except: pass
            raise
        rev = ckan.models.repo.youngest_revision()
        self.outpkg = rev.model.packages.get(self.testname2)

    def teardown_class(self):
        rev = ckan.models.repo.youngest_revision()
        rev.model.packages.purge(self.testname2)

    def test_to_python_tags_delete_and_keep(self):
        taglist = []
        for xx in self.outpkg.tags:
            taglist.append(xx.tag.name)
        assert u'russian' not in taglist
        assert u'tolstoy' in taglist

