import ckan.model as model
import ckan.forms
from ckan.tests import *
from ckan.tests.pylons_controller import PylonsTestCase
from ckan.tests.html_check import HtmlCheckMethods
from ckan.lib.helpers import escape

def _get_blank_param_dict(pkg=None):
    return ckan.forms.get_package_dict(pkg=pkg, blank=True, user_editable_groups=[])

# These tests check the package form build in formalchemy. For the new forms,
# see equivalents:
#  * form renders with correctly populated values (TestForms 1&2) in ckan/tests/functional/test_package.py:TestPackageForm
#  * form post updates db correctly (TestForms 3&4) in ckan/tests/functional/api/test_action.py:test_03_create_update_package
#  * validation tests (TestValidation) in ckan/tests/schema/test_schema.py

class TestForms(PylonsTestCase, HtmlCheckMethods):

    @classmethod
    def setup_class(cls):
        super(TestForms, cls).setup_class()
        model.Session.remove()
        ckan.tests.CreateTestData.create()

    @classmethod
    def teardown_class(cls):
        super(TestForms, cls).teardown_class()
        model.Session.remove()
        model.repo.rebuild_db()

    def _get_standard_fieldset(self):
        fs = ckan.forms.get_standard_fieldset(user_editable_groups=[])
        return fs

    def test_0_get_package_dict(self):
        d = ckan.forms.get_package_dict(user_editable_groups=[])
        assert 'Package--title' in d
        assert not 'Package--all_revisions' in d

        anna = model.Package.by_name(u'annakarenina')
        prefix = 'Package-%s-' % anna.id
        d = ckan.forms.get_package_dict(anna, user_editable_groups=[])
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
        fs = self._get_standard_fieldset()
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
        fs = self._get_standard_fieldset()
        anna = model.Package.by_name(u'annakarenina')
        fs = fs.bind(anna)
        out = fs.notes.render()

    def test_2_name(self):
        fs = self._get_standard_fieldset()
        anna = model.Package.by_name(u'annakarenina')
        fs = fs.bind(anna)
        out = fs.render()
        assert 'Name' in out, out
        assert '*' in out, out

    def test_2_tags(self):
        fs = self._get_standard_fieldset()
        anna = model.Package.by_name(u'annakarenina')
        fs = fs.bind(anna)
        out = fs.tags.render()
        assert out
        assert 'tags' in out
        self.check_tag(out, 'input', 'russian', 'tolstoy')

        out = fs.tags.render_readonly()
        self.check_tag(out, 'a', '/tag/russian')
        self.check_tag(out, 'a', '/tag/tolstoy')
        self.check_named_element(out, 'a', '>russian<')

    def test_2_resources(self):
        fs = self._get_standard_fieldset()
        anna = model.Package.by_name(u'annakarenina')
        fs = fs.bind(anna)
        out = fs.resources.render()
        out_printable = out.encode('utf8') # encoded utf8
        for res in anna.resources:
            assert escape(res.url) in out, out_printable
            assert res.format in out, out_printable
            assert u'Full text. Needs escaping: &#34; Umlaut: \xfc"' in out, out_printable        
            assert res.hash in out, out_printable        
            assert res.alt_url in out, out_printable        
            assert res.extras['size_extra'] in out, out_printable        

    def test_2_fields(self):
        fs = self._get_standard_fieldset()
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
        indict['Package--tags'] = u'russian, tolstoy, ' + newtagname,
        indict['Package--license_id'] = u'gpl-3.0'
        indict['Package--extras-newfield0-key'] = u'testkey'
        indict['Package--extras-newfield0-value'] = u'testvalue'
        indict['Package--resources-0-url'] = u'http:/1'
        indict['Package--resources-0-format'] = u'xml'
        indict['Package--resources-0-description'] = u'test desc'
        indict['Package--resources-0-size'] = 10
        indict['Package--resources-0-alt_url'] = u'http:/2'

        fs = self._get_standard_fieldset().bind(model.Package, data=indict)

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
        assert res.alt_url == u'http:/2', res.format
        

    def test_4_sync_update(self):
        newtagname = 'newtagname'
        anna = model.Package.by_name(u'annakarenina')
        prefix = 'Package-%s-' % anna.id
        indict = _get_blank_param_dict(anna)
        indict[prefix + 'name'] = u'annakaren'
        indict[prefix + 'notes'] = u'new notes'
        indict[prefix + 'tags'] = u'russian ,' + newtagname
        indict[prefix + 'license_id'] = u'gpl-3.0'
        indict[prefix + 'extras-newfield0-key'] = u'testkey'
        indict[prefix + 'extras-newfield0-value'] = u'testvalue'
        indict[prefix + 'resources-0-url'] = u'http:/1'
        indict[prefix + 'resources-0-format'] = u'xml'
        indict[prefix + 'resources-0-description'] = u'test desc'
        indict[prefix + 'resources-0-alt_url'] = u'alt'
        
        fs = self._get_standard_fieldset().bind(anna, data=indict)
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
        assert res.alt_url == u'alt', res.description

        model.repo.commit_and_remove()

class TestFormErrors(PylonsTestCase):
    @classmethod
    def setup_class(self):
        model.Session.remove()
        ckan.tests.CreateTestData.create()

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()

    def _get_standard_fieldset(self):
        fs = ckan.forms.get_standard_fieldset(user_editable_groups=[])
        return fs

    def test_1_dup_name(self):
        assert model.Package.by_name(u'annakarenina')
        indict = _get_blank_param_dict()
        prefix = 'Package--'
        indict[prefix + 'name'] = u'annakarenina'
        indict[prefix + 'title'] = u'Some title'
        fs = self._get_standard_fieldset().bind(model.Package, data=indict)
        model.repo.new_revision()
        assert not fs.validate()

    def test_1_new_name(self):
        indict = _get_blank_param_dict()
        prefix = 'Package--'
        indict[prefix + 'name'] = u'annakarenina123'
        indict[prefix + 'title'] = u'Some title'
        fs = self._get_standard_fieldset().bind(model.Package, data=indict)
        model.repo.new_revision()
        assert fs.validate()

    def test_2_extra_no_key(self):
        indict = _get_blank_param_dict()
        prefix = 'Package--'
        indict[prefix + 'name'] = u'annakarenina123'
        indict[prefix + 'title'] = u'Some title'
        indict[prefix + 'extras-newfield0-value'] = u'testvalue'
        fs = self._get_standard_fieldset().bind(model.Package, data=indict)
        model.repo.new_revision()
        assert not fs.validate()

    def test_2_extra_no_value(self):
        indict = _get_blank_param_dict()
        prefix = 'Package--'
        indict[prefix + 'name'] = u'annakarenina123'
        indict[prefix + 'title'] = u'Some title'
        indict[prefix + 'extras-newfield0-key'] = u'testkey'
        fs = self._get_standard_fieldset().bind(model.Package, data=indict)
        model.repo.new_revision()
        assert fs.validate()

    def test_2_extra_key(self):
        indict = _get_blank_param_dict()
        prefix = 'Package--'
        indict[prefix + 'name'] = u'annakarenina123'
        indict[prefix + 'title'] = u'Some title'
        indict[prefix + 'extras-newfield0-value'] = u'testvalue'
        indict[prefix + 'extras-newfield0-key'] = u'testkey'
        fs = self._get_standard_fieldset().bind(model.Package, data=indict)
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
        fs = self._get_standard_fieldset().bind(model.Package, data=indict)
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

    def _get_standard_fieldset(self):
        fs = ckan.forms.get_standard_fieldset(user_editable_groups=[])
        return fs

    def test_1_package_name(self):
        anna = model.Package.by_name(u'annakarenina')
        prefix = 'Package-%s-' % anna.id
        indict = _get_blank_param_dict(anna)

        good_names = [ 'blah', 'ab', 'ab1', 'some-random-made-up-name', 'has_underscore', 'annakarenina' ]
        bad_names = [ '', 'blAh', 'a', 'dot.in.name', u'unicode-\xe0', 'percent%' ]

        for i, name in enumerate(good_names):
            indict[prefix + 'name'] = unicode(name)
            fs = self._get_standard_fieldset().bind(anna, data=indict)
            assert fs.validate()

        for i, name in enumerate(bad_names):
            indict[prefix + 'name'] = unicode(name)
            fs = self._get_standard_fieldset().bind(anna, data=indict)
            assert not fs.validate()

    def test_1_tag_name(self):
        anna = model.Package.by_name(u'annakarenina')
        prefix = 'Package-%s-' % anna.id
        indict = _get_blank_param_dict(anna)

        good_names = [ 'blah', 'ab', 'ab1', 'some-random-made-up-name',\
                       'has_underscore', u'unicode-\xe0', 'dot.in.name',\
                       'multiple words', u'with Greek omega \u03a9', 'CAPITALS']
        bad_names = [ 'a', '  ,leading comma', 'trailing comma,',\
                      'empty,,tag' 'quote"character']

        for i, name in enumerate(good_names):
            indict[prefix + 'name'] = u'okname'
            indict[prefix + 'tags'] = unicode(name)
            fs = self._get_standard_fieldset().bind(anna, data=indict)
            out = fs.validate()
            assert out, fs.errors

        for i, name in enumerate(bad_names):
            indict[prefix + 'name'] = u'okname'
            indict[prefix + 'tags'] = unicode(name)
            fs = self._get_standard_fieldset().bind(anna, data=indict)
            out = fs.validate()
            assert not out, fs.errors

    def test_2_tag_names_are_stripped_of_leading_and_trailing_spaces(self):
        """
        Asserts that leading and trailing spaces are stripped from tag names
        """
        anna = model.Package.by_name(u'annakarenina')
        prefix = 'Package-%s-' % anna.id
        indict = _get_blank_param_dict(anna)
        indict[prefix + 'name'] = u'annakarenina'

        whitespace_characters = u'\t\n\r\f\v'
        for ch in whitespace_characters:
            indict[prefix + 'tags'] = ch + u'tag name' + ch
            fs = self._get_standard_fieldset().bind(anna, data=indict)
            out = fs.validate()
            assert out, fs.errors

            model.repo.new_revision()
            fs.sync()
            model.repo.commit_and_remove()
            anna = model.Package.by_name(u'annakarenina')
            taglist = [ tag.name for tag in anna.tags ]
            assert len(taglist) == 1
            assert u'tag name' in taglist

    def test_3_tag_names_are_split_by_commas(self):
        """
        Asserts that tag names are split by commas.
        """
        anna = model.Package.by_name(u'annakarenina')
        prefix = 'Package-%s-' % anna.id
        indict = _get_blank_param_dict(anna)
        indict[prefix + 'name'] = u'annakarenina'

        indict[prefix + 'tags'] = u'tag name one, tag name two'
        fs = self._get_standard_fieldset().bind(anna, data=indict)
        out = fs.validate()
        assert out, fs.errors

        model.repo.new_revision()
        fs.sync()
        model.repo.commit_and_remove()
        anna = model.Package.by_name(u'annakarenina')
        taglist = [ tag.name for tag in anna.tags ]
        assert len(taglist) == 2
        assert u'tag name one' in taglist
        assert u'tag name two' in taglist

