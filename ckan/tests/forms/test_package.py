import py.test
import formencode

import ckan.model as model
import ckan.tests
import ckan.forms

class TestPackageName:

    unique = ckan.forms.UniquePackageName()
    lower = ckan.forms.LowerCase()
    schema = ckan.forms.PackageNameSchema()
    bad_names = [ '', 'blAh', 'a', 'annakarenina' ]
    good_names = [ 'blah', 'ab', 'ab1', 'some-random-made-up-name' ]
    
    @classmethod
    def setup_class(self):
        model.Session.remove()
        ckan.tests.CreateTestData.create()

    @classmethod
    def teardown_class(self):
        ckan.tests.CreateTestData.delete()

    def _check_raises(self, fn, name):
        print name
        py.test.raises(formencode.Invalid, fn, name)

    def test_lower_case_raises(self):
        print 'In lower case raises'
        print model.Package.query.all()
        self._check_raises(self.lower.to_python, self.bad_names[1])

    def test_lower_case_ok(self):
        self.lower.to_python(self.good_names[0])

    def test_std_object_name(self):
        bad_names = [ 'blAh', 'a', 'geodata,' ]
        good_names = [ 'blah', 'ab', 'ab1', 'some-random-made-up-name' ]
        validator = ckan.forms.std_object_name.to_python
        for name in bad_names:
            self._check_raises(validator, name)
        for name in good_names:
            validator(name)

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
        ckan.tests.CreateTestData.create()
        self.schema = ckan.forms.PackageSchema()
        self.name = u'annakarenina'
        self.pkg = model.Package.by_name(self.name)
        self.out = self.schema.from_python(self.pkg)
        active = model.State.query.filter_by(name='active').one()
        self.exp = {
                'id'      : self.pkg.id,
                'title'   : self.pkg.title,
                'version' : self.pkg.version,
                'url'     : self.pkg.url,
                'download_url'     : self.pkg.download_url,
                'notes'   : self.pkg.notes,
                'state_id'   : active.id,
                'name'    : self.pkg.name,
                'tags'    : u'russian tolstoy',
                'licenses': [ 'OKD Compliant::Other' ],
                'license_id' : self.pkg.license_id,
                'revision_id': self.pkg.revision_id
                }

    @classmethod
    def teardown_class(self):
        ckan.tests.CreateTestData.delete()
        model.Session.remove()

    def _check_from_python(self, key):
        assert self.out[key] == self.exp[key]

    def test_from_python(self):
        print 'out', self.out
        print 'exp', self.exp
        keys = self.exp.keys()
        assert len(keys) == len(self.out.keys())
        for key in keys:
            self._check_from_python(key) 


class TestPackageSchemaToPythonNew:
    schema = ckan.forms.PackageSchema()
    testname = u'schematestpkg'
    newtagname = u'schematesttag'

    @classmethod
    def setup_class(self):
        txn = model.repo.new_revision()
        self.indict = {
                'name' : self.testname,
                'notes': u'some new notes',
                'tags' : u'russian tolstoy, ' + self.newtagname,
                'licenses': [ 'OKD Compliant::Other' ] 
                }
        try: # wrap this so that teardown still gets called if there is an error
            # self.testpkg = txn.model.packages.create(name=self.testname)
            self.schema.to_python(self.indict)
            model.repo.commit_and_remove()
        except Exception, inst:
            model.Session.remove()
            model.repo.rebuild_db()
            raise
        rev = model.repo.youngest_revision()

    @classmethod
    def teardown_class(self):
        model.Session.remove()
        model.repo.rebuild_db()

    def test_to_python(self):
        outpkg = model.Package.by_name(self.testname)
        outpkg.notes == self.indict['notes']

    def test_to_python_tags(self):
        outpkg = model.Package.by_name(self.testname)
        taglist = [ tag.name for tag in outpkg.tags ]
        assert u'russian' in taglist
        assert u'tolstoy' in taglist
        assert self.newtagname in taglist

    def test_to_python_licenses(self):
        outpkg = model.Package.by_name(self.testname)
        out = [ outpkg.license.name ]
        assert self.indict['licenses'] == out


class TestPackageSchemaToPythonUpdate:
    schema = ckan.forms.PackageSchema()
    pkgname = u'annakarenina'

    @classmethod
    def setup_class(self):
        ckan.tests.CreateTestData.create()
        model.Session.remove()
        anna = model.Package.by_name(self.pkgname)
        # has 2 tags: russian and tolstoy
        indict2 = {
            'id'   : anna.id,
            'name' : self.pkgname,
            'tags' : u'tolstoy',
        }
        try:
            model.repo.new_revision()
            self.schema.to_python(indict2)
            model.repo.commit_and_remove()
        except:
            model.Session.remove()
            model.repo.rebuild_db()
            raise

    @classmethod
    def teardown_class(self):
        model.Session.remove()
        ckan.tests.CreateTestData.delete()
        model.Session.remove()

    def test_to_python_tags_delete_and_keep(self):
        outpkg = model.Package.by_name(self.pkgname)
        taglist = [ tag.name for tag in outpkg.tags ]
        assert u'russian' not in taglist
        assert u'tolstoy' in taglist

    def test_bad_tag_name_does_not_work(self):
        outpkg = model.Package.by_name(self.pkgname)
        ok = False
        try:
            indict2 = {
                    'id'   : outpkg.id,
                    'name' : 'annakarenina',
                    'tags' : u'tolstoy%%',
                    }
            self.schema.to_python(indict2)
        except formencode.Invalid, inst:
            ok = True
        if not ok:
            assert False, 'Failed to raise an exception given bad tag name'

