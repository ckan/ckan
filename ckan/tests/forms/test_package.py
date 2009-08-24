import ckan.model as model
import ckan.forms
from ckan.tests import *

    

def _get_basic_dict(pkg=None):
    indict = {}
    if pkg:
        fs = ckan.forms.package_fs.bind(pkg)
    else:
        fs = ckan.forms.package_fs

    exclude = ('-id', '-package_tags', '-all_revisions')

    for field in fs._fields.values():
        if not filter(lambda x: field.renderer.name.endswith(x), exclude):
            indict[field.renderer.name] = u'' #field.renderer.stringify_value(field.renderer._value)
    return indict

class TestForms:
    @classmethod
    def setup_class(self):
        model.Session.remove()
        ckan.tests.CreateTestData.create()

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()

    def test_0_get_package_dict(self):
        d = ckan.forms.get_package_dict()
        assert 'Package--title' in d
        assert not 'Package--all_revisions' in d

        anna = model.Package.by_name(u'annakarenina')
        prefix = 'Package-%s-' % anna.id
        d = ckan.forms.get_package_dict(anna)
        assert prefix+'title' in d
        assert d[prefix+'title'] == anna.title
        assert d[prefix+'version'] == anna.version
        assert d[prefix+'url'] == anna.url

        changes = {'title':'newtitle', 'url':'newurl'}
        d2 = ckan.forms.edit_package_dict(d, changes, anna.id)
        assert d2[prefix+'title'] == changes['title']
        assert d2[prefix+'version'] == anna.version
        assert d2[prefix+'url'] == changes['url']
        assert d2[prefix+'name'] == anna.name

    def test_1_render(self):
        fs = ckan.forms.package_fs
        anna = model.Package.by_name(u'annakarenina')
        fs = fs.bind(anna)
        out = fs.render()
        assert out
        assert 'Revision' not in out, out
#        assert 'revision_id' not in out, out
        assert 'All revisions' not in out, out
#        assert 'all_revisions' not in out, out
        assert 'Package tags' not in out, out

    def test_2_name(self):
        fs = ckan.forms.package_fs
        anna = model.Package.by_name(u'annakarenina')
        fs = fs.bind(anna)
        out = fs.render()
        assert 'Name (required)' in out, out

    def test_2_tags(self):
        fs = ckan.forms.package_fs
        anna = model.Package.by_name(u'annakarenina')
        fs = fs.bind(anna)
        out = fs.tags.render()
        print out
        assert out
        assert 'tags' in out
        assert 'value="russian tolstoy"' in out

    def test_2_fields(self):
        fs = ckan.forms.package_fs
        anna = model.Package.by_name(u'annakarenina')
        fs = fs.bind(anna)
        out = fs.render()
#        print out
        assert out
        assert 'title' in fs.title.render(), fs.title.render()
        assert anna.title in fs.title.render(), fs.title.render()
        assert 'version' in fs.version.render(), fs.version.render()
        assert anna.version in fs.version.render(), fs.version.render()
        assert 'notes' in fs.notes.render(), fs.notes.render()
        assert anna.notes in fs.notes.render(), fs.notes.render()
        assert 'name' in fs.name.render(), fs.name.render()
        assert anna.name in fs.name.render(), fs.name.render()
        assert 'tags' in fs.tags.render(), fs.tags.render()
        
    def test_3_sync_new(self):
        newtagname = 'newtagname'
        indict = _get_basic_dict()
        indict['Package--name'] = u'testname'
        indict['Package--notes'] = u'some new notes'
        indict['Package--tags'] = u'russian tolstoy, ' + newtagname,
        indict['Package--license_id'] = '1'

        fs = ckan.forms.package_fs.bind(model.Package, data=indict)

        model.repo.new_revision()
        fs.sync()
        outpkg = fs.model

        assert outpkg.notes == indict['Package--notes']

        # test tags
        taglist = [ tag.name for tag in outpkg.tags ]
        assert u'russian' in taglist, taglist
        assert u'tolstoy' in taglist, taglist
        assert newtagname in taglist

        # test licenses
        assert outpkg.license
        assert indict['Package--license_id'] == str(outpkg.license.id), outpkg.license.id

        model.repo.commit_and_remove()

    def test_4_sync_update(self):
        newtagname = 'newtagname'
        anna = model.Package.by_name(u'annakarenina')
        prefix = 'Package-%s-' % anna.id
        indict = _get_basic_dict(anna)
        indict[prefix + 'name'] = u'annakaren'
        indict[prefix + 'notes'] = u'new notes'
        indict[prefix + 'tags'] = u'russian ' + newtagname
        indict[prefix + 'license_id'] = '1'
        
        fs = ckan.forms.package_fs.bind(anna, data=indict)
        model.repo.new_revision()
        fs.sync()
        model.repo.commit_and_remove()
        outpkg = model.Package.by_name(u'annakaren')
        assert outpkg
        outpkg1 = model.Package.by_name(u'annakarenina')
        assert not outpkg1

        assert outpkg.notes == indict[prefix+'notes']

        # test tags
        taglist = [ tag.name for tag in outpkg.tags ]
        assert u'russian' in taglist, taglist
        assert u'tolstoy' not in taglist, taglist
        assert newtagname in taglist

        # test licenses
        assert outpkg.license
        assert indict[prefix+'license_id'] == str(outpkg.license.id), outpkg.license.id

        model.repo.commit_and_remove()

class TestFormErrors:
    @classmethod
    def setup_class(self):
        model.Session.remove()
        ckan.tests.CreateTestData.create()

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()

    def test_1_dup_name(self):
        assert model.Package.by_name(u'annakarenina')
        indict = _get_basic_dict()
        prefix = 'Package--'
        indict[prefix + 'name'] = u'annakarenina'
        indict[prefix + 'title'] = u'Some title'
        fs = ckan.forms.package_fs.bind(model.Package, data=indict)
        model.repo.new_revision()
        assert not fs.validate()

    def test_1_new_name(self):
        indict = _get_basic_dict()
        prefix = 'Package--'
        indict[prefix + 'name'] = u'annakarenina123'
        indict[prefix + 'title'] = u'Some title'
        fs = ckan.forms.package_fs.bind(model.Package, data=indict)
        model.repo.new_revision()
        assert fs.validate()


class TestValidation:
    @classmethod
    def setup_class(self):
        model.Session.remove()
        ckan.tests.CreateTestData.create()

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()

    def test_1_package_name(self):
        anna = model.Package.by_name(u'annakarenina')
        prefix = 'Package-%s-' % anna.id
        indict = _get_basic_dict(anna)

        good_names = [ 'blah', 'ab', 'ab1', 'some-random-made-up-name', 'has_underscore' ]
        bad_names = [ '', 'blAh', 'a', 'annakarenina', 'dot.in.name', u'unicode-\xe0', 'percent%' ]

        for i, name in enumerate(good_names):
            print "Good name:", i
            indict[prefix + 'name'] = unicode(name)
            fs = ckan.forms.package_fs.bind(anna, data=indict)
            assert fs.validate()

        for i, name in enumerate(bad_names):
            print "Bad name:", i
            indict[prefix + 'name'] = unicode(name)
            fs = ckan.forms.package_fs.bind(anna, data=indict)
            assert not fs.validate()

    def test_1_tag_name(self):
        anna = model.Package.by_name(u'annakarenina')
        prefix = 'Package-%s-' % anna.id
        indict = _get_basic_dict(anna)

        good_names = [ 'blah', 'ab', 'ab1', 'some-random-made-up-name', 'has_underscore', u'unicode-\xe0', 'dot.in.name' ]
        bad_names = [ 'a', 'blAh', 'percent%' ]

        for i, name in enumerate(good_names):
            print "Good tag name:", i
            indict[prefix + 'name'] = u'okname'
            indict[prefix + 'tags'] = unicode(name)
            fs = ckan.forms.package_fs.bind(anna, data=indict)
            out = fs.validate()
            assert out, fs.errors

        for i, name in enumerate(bad_names):
            print "Bad tag name:", i
            indict[prefix + 'name'] = u'okname'
            indict[prefix + 'tags'] = unicode(name)
            fs = ckan.forms.package_fs.bind(anna, data=indict)
            out = fs.validate()
            assert not out, fs.errors
            
