import ckan.model as model
import ckan.forms
from ckan.tests import *
from ckan.tests.pylons_controller import PylonsTestCase
from ckan.lib.helpers import escape

def _get_blank_param_dict(pkg=None):
    return ckan.forms.get_package_dict(pkg=pkg, blank=True)

class TestForms(PylonsTestCase):
    @classmethod
    def setup_class(self):
        model.Session.remove()
        ckan.tests.CreateTestData.create()

    @classmethod
    def teardown_class(self):
        model.Session.remove()
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
        fs = ckan.forms.get_standard_fieldset()
        anna = model.Package.by_name(u'annakarenina')
        fs = fs.bind(anna)
        out = fs.render()
        assert out
        assert 'Revision' not in out, out
#        assert 'revision_id' not in out, out
        assert 'All revisions' not in out, out
#        assert 'all_revisions' not in out, out
        assert 'Package tags' not in out, out

    def test_1_render_markdown(self):
        fs = ckan.forms.get_standard_fieldset()
        anna = model.Package.by_name(u'annakarenina')
        fs = fs.bind(anna)
        out = fs.notes.render()
        print out

    def test_2_name(self):
        fs = ckan.forms.get_standard_fieldset()
        anna = model.Package.by_name(u'annakarenina')
        fs = fs.bind(anna)
        out = fs.render()
        assert 'Name (required)' in out, out

    def test_2_tags(self):
        fs = ckan.forms.get_standard_fieldset()
        anna = model.Package.by_name(u'annakarenina')
        fs = fs.bind(anna)
        out = fs.tags.render()
        print out
        assert out
        assert 'tags' in out
        self.check_tag(out, 'russian', 'tolstoy')

    def test_2_resources(self):
        fs = ckan.forms.get_standard_fieldset()
        anna = model.Package.by_name(u'annakarenina')
        fs = fs.bind(anna)
        out = fs.resources.render()
        # out is str, but it contains unicode characters
        out = unicode(out, 'utf8') # now it's unicode type
        out_printable = out.encode('utf8') # encoded utf8
        for res in anna.resources:
            assert escape(res.url) in out, out_printable
            assert res.format in out, out_printable
            assert u'Full text. Needs escaping: &#34; Umlaut: \xfc"' in out, out_printable        
            assert res.hash in out, out_printable        

    def test_2_fields(self):
        fs = ckan.forms.get_standard_fieldset()
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
        assert anna.notes[:10] in fs.notes.render(), fs.notes.render()
        assert 'name' in fs.name.render(), fs.name.render()
        assert anna.name in fs.name.render(), fs.name.render()
        assert 'tags' in fs.tags.render(), fs.tags.render()
        assert 'extras' in fs.extras.render(), fs.extras.render()
        extra = anna._extras.values()[0]
        assert extra.key in fs.extras.render(), fs.extras.render()
        assert extra.value in fs.extras.render(), fs.extras.render()
        assert 'Delete' in fs.extras.render(), fs.extras.render()
        
    def test_3_sync_new(self):
        newtagname = 'newtagname'
        indict = _get_blank_param_dict()
        indict['Package--name'] = u'testname'
        indict['Package--notes'] = u'some new notes'
        indict['Package--tags'] = u'russian tolstoy, ' + newtagname,
        indict['Package--license_id'] = u'gpl-3.0'
        indict['Package--extras-newfield0-key'] = u'testkey'
        indict['Package--extras-newfield0-value'] = u'testvalue'
        indict['Package--resources-0-url'] = u'http:/1'
        indict['Package--resources-0-format'] = u'xml'
        indict['Package--resources-0-description'] = u'test desc'
        fs = ckan.forms.get_standard_fieldset().bind(model.Package, data=indict)

        model.repo.new_revision()
        fs.sync()
        model.repo.commit_and_remove()

        outpkg = model.Package.by_name(u'testname')
        assert outpkg.notes == indict['Package--notes']

        # test tags
        taglist = [ tag.name for tag in outpkg.tags ]
        assert u'russian' in taglist, taglist
        assert u'tolstoy' in taglist, taglist
        assert newtagname in taglist

        # test licenses
        assert indict['Package--license_id'] == outpkg.license_id, outpkg.license_id
        #assert outpkg.license
        #assert indict['Package--license_id'] == outpkg.license.id, outpkg.license

        # test extra
        assert outpkg._extras.keys() == [u'testkey'], outpkg._extras.keys()
        assert outpkg._extras.values()[0].key == u'testkey', outpkg._extras.values()[0].key
        assert outpkg._extras.values()[0].value == u'testvalue', outpkg._extras.values()[0].value

        # test resources
        assert len(outpkg.resources) == 1, outpkg.resources
        res = outpkg.resources[0]
        assert res.url == u'http:/1', res.url
        assert res.description == u'test desc', res.description
        assert res.format == u'xml', res.format
        

    def test_4_sync_update(self):
        newtagname = 'newtagname'
        anna = model.Package.by_name(u'annakarenina')
        prefix = 'Package-%s-' % anna.id
        indict = _get_blank_param_dict(anna)
        indict[prefix + 'name'] = u'annakaren'
        indict[prefix + 'notes'] = u'new notes'
        indict[prefix + 'tags'] = u'russian ' + newtagname
        indict[prefix + 'license_id'] = u'gpl-3.0'
        indict[prefix + 'extras-newfield0-key'] = u'testkey'
        indict[prefix + 'extras-newfield0-value'] = u'testvalue'
        indict[prefix + 'resources-0-url'] = u'http:/1'
        indict[prefix + 'resources-0-format'] = u'xml'
        indict[prefix + 'resources-0-description'] = u'test desc'
        
        fs = ckan.forms.get_standard_fieldset().bind(anna, data=indict)
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
        assert indict[prefix+'license_id'] == outpkg.license.id, outpkg.license

        # test extra
        assert outpkg.extras.has_key(u'testkey'), outpkg._extras.keys()
        assert outpkg.extras[u'testkey'] == u'testvalue', outpkg._extras.values()[0].value

        # test resources
        assert len(outpkg.resources) == 1, outpkg.resources
        res = outpkg.resources[0]
        assert res.url == u'http:/1', res.url
        assert res.description == u'test desc', res.description
        assert res.format == u'xml', res.format

        model.repo.commit_and_remove()

class TestFormErrors(PylonsTestCase):
    @classmethod
    def setup_class(self):
        model.Session.remove()
        ckan.tests.CreateTestData.create()

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()

    def test_1_dup_name(self):
        assert model.Package.by_name(u'annakarenina')
        indict = _get_blank_param_dict()
        prefix = 'Package--'
        indict[prefix + 'name'] = u'annakarenina'
        indict[prefix + 'title'] = u'Some title'
        fs = ckan.forms.get_standard_fieldset().bind(model.Package, data=indict)
        model.repo.new_revision()
        assert not fs.validate()

    def test_1_new_name(self):
        indict = _get_blank_param_dict()
        prefix = 'Package--'
        indict[prefix + 'name'] = u'annakarenina123'
        indict[prefix + 'title'] = u'Some title'
        fs = ckan.forms.get_standard_fieldset().bind(model.Package, data=indict)
        model.repo.new_revision()
        assert fs.validate()

    def test_2_extra_no_key(self):
        indict = _get_blank_param_dict()
        prefix = 'Package--'
        indict[prefix + 'name'] = u'annakarenina123'
        indict[prefix + 'title'] = u'Some title'
        indict[prefix + 'extras-newfield0-value'] = u'testvalue'
        fs = ckan.forms.get_standard_fieldset().bind(model.Package, data=indict)
        model.repo.new_revision()
        assert not fs.validate()

    def test_2_extra_no_value(self):
        indict = _get_blank_param_dict()
        prefix = 'Package--'
        indict[prefix + 'name'] = u'annakarenina123'
        indict[prefix + 'title'] = u'Some title'
        indict[prefix + 'extras-newfield0-key'] = u'testkey'
        fs = ckan.forms.get_standard_fieldset().bind(model.Package, data=indict)
        model.repo.new_revision()
        assert fs.validate()

    def test_2_extra_key(self):
        indict = _get_blank_param_dict()
        prefix = 'Package--'
        indict[prefix + 'name'] = u'annakarenina123'
        indict[prefix + 'title'] = u'Some title'
        indict[prefix + 'extras-newfield0-value'] = u'testvalue'
        indict[prefix + 'extras-newfield0-key'] = u'testkey'
        fs = ckan.forms.get_standard_fieldset().bind(model.Package, data=indict)
        model.repo.new_revision()
        assert fs.validate(), fs.errors

    def test_3_resource_no_url(self):
        indict = _get_blank_param_dict()
        prefix = 'Package--'
        indict[prefix + 'name'] = u'annakarenina123'
        indict[prefix + 'title'] = u'Some title'
        indict[prefix + 'resources-'] = u'testvalue'
        indict['Package--resources-0-url'] = u''
        indict['Package--resources-0-format'] = u'xml'
        indict['Package--resources-0-description'] = u'test desc'
        fs = ckan.forms.get_standard_fieldset().bind(model.Package, data=indict)
        model.repo.new_revision()
        assert not fs.validate()

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
        indict = _get_blank_param_dict(anna)

        good_names = [ 'blah', 'ab', 'ab1', 'some-random-made-up-name', 'has_underscore', 'annakarenina' ]
        bad_names = [ '', 'blAh', 'a', 'dot.in.name', u'unicode-\xe0', 'percent%' ]

        for i, name in enumerate(good_names):
            print "Good name:", i
            indict[prefix + 'name'] = unicode(name)
            fs = ckan.forms.get_standard_fieldset().bind(anna, data=indict)
            assert fs.validate()

        for i, name in enumerate(bad_names):
            print "Bad name:", i
            indict[prefix + 'name'] = unicode(name)
            fs = ckan.forms.get_standard_fieldset().bind(anna, data=indict)
            assert not fs.validate()

    def test_1_tag_name(self):
        anna = model.Package.by_name(u'annakarenina')
        prefix = 'Package-%s-' % anna.id
        indict = _get_blank_param_dict(anna)

        good_names = [ 'blah', 'ab', 'ab1', 'some-random-made-up-name', 'has_underscore', u'unicode-\xe0', 'dot.in.name', 'blAh' ] # nb: becomes automatically lowercase
        bad_names = [ 'a', 'percent%' ]

        for i, name in enumerate(good_names):
            print "Good tag name:", i
            indict[prefix + 'name'] = u'okname'
            indict[prefix + 'tags'] = unicode(name)
            fs = ckan.forms.get_standard_fieldset().bind(anna, data=indict)
            out = fs.validate()
            assert out, fs.errors

        for i, name in enumerate(bad_names):
            print "Bad tag name:", i
            indict[prefix + 'name'] = u'okname'
            indict[prefix + 'tags'] = unicode(name)
            fs = ckan.forms.get_standard_fieldset().bind(anna, data=indict)
            out = fs.validate()
            assert not out, fs.errors
            
