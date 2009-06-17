from ckan.tests import *
import ckan.model as model

import cgi
from paste.fixture import AppError

class TestPackageController(TestController2):

    @classmethod
    def setup_class(self):
        CreateTestData.create()

    @classmethod
    def teardown_class(self):
        CreateTestData.delete()

    def test_index(self):
        offset = url_for(controller='package')
        res = self.app.get(offset)
        assert 'Packages - Index' in res

    def test_sidebar(self):
        offset = url_for(controller='package')
        res = self.app.get(offset)
        # sidebar
        assert 'Packages section' in res

    def test_minornavigation(self):
        offset = url_for(controller='package')
        res = self.app.get(offset)
        # TODO: make this a bit more rigorous!
        assert 'List' in res
        res = res.click('List')
        assert 'Packages - List' in res
    
    def test_minornavigation_2(self):
        offset = url_for(controller='package')
        res = self.app.get(offset)
        res = res.click('New')
        assert 'Packages - New' in res

    def test_read(self):
        name = 'annakarenina'
        offset = url_for(controller='package', action='read', id=name)
        res = self.app.get(offset)
        # only retrieve after app has been called
        self.anna = model.Package.by_name(name)
        print res
        assert 'Packages - %s' % name in res
        assert name in res
        assert self.anna.version in res
        assert 'Url:' in res
        assert self.anna.url in res
        assert cgi.escape(self.anna.download_url) in res
        assert 'Notes:' in res
        assert 'Some test notes' in res
        assert '<strong>Some bolded text.</strong>' in res
        assert 'Licenses:' in res
        assert 'OKD Compliant::' in res
        assert 'Tags:' in res
        assert 'russian' in res

    def test_read_nonexistentpackage(self):
        name = 'anonexistentpackage'
        offset = url_for(controller='package', action='read', id=name)
        res = self.app.get(offset, status=404)

    def test_list(self):
        offset = url_for(controller='package', action='list')
        res = self.app.get(offset)
        assert 'Packages - List' in res
        name = 'annakarenina'
        assert name in res
        res = res.click(name)
        assert 'Packages - %s' % name in res

    def test_search(self):
        offset = url_for(controller='package', action='search')
        res = self.app.get(offset)
        assert 'Packages - Search' in res
        self._check_search_results(res, 'anna', ['1 result', 'annakarenina'] )
        self._check_search_results(res, 'war', ['1 result', 'warandpeace'] )
        self._check_search_results(res, 'a', ['2 results', 'warandpeace', 'annakarenina'] )
        self._check_search_results(res, 'n', ['2 results', 'warandpeace', 'annakarenina'] )
        self._check_search_results(res, '', ['0 results'] )
        self._check_search_results(res, 'z', ['0 results'] )
        self._check_search_results(res, 'A Novel By Tolstoy', ['1 result'] )
        self._check_search_results(res, 'title:Novel', ['1 result'] )
        self._check_search_results(res, 'title:peace', ['0 results'] )
        # Not working, not needed....?
        #self._check_search_results(res, 'name:peace', ['1 result'] )

    def _check_search_results(self, page, terms, requireds):
        form = page.forms[0]
        form['q'] =  str(terms)
        results_page = form.submit()
        assert 'Packages - Search' in results_page, results_page
        for required in requireds:
            print results_page
            assert required in results_page, (required, results_page)
    
    def test_history(self):
        name = 'annakarenina'
        offset = url_for(controller='package', action='history', id=name)
        res = self.app.get(offset)
        assert 'History' in res
        assert 'Revisions' in res
        assert name in res


class TestPackageControllerEdit(TestController2):
    def setup_method(self, method):
        self.setUp()

    def setUp(self):
        rev = model.repo.new_revision()
        self.editpkg_name = u'editpkgtest'
        self.editpkg = model.Package(name=self.editpkg_name)
        self.editpkg.url = u'editpkgurl.com'
        self.editpkg.notes= u'this is editpkg'
        model.Session.commit()
        model.Session.remove()
        offset = url_for(controller='package', action='edit', id=self.editpkg.name)
        self.res = self.app.get(offset)
        self.newtagname = 'russian'

    def teardown_method(self, method):
        self.tearDown()

    def tearDown(self):
        pkg = model.Package.by_name(self.editpkg.name)
        if pkg:
            pkg.purge()
        tag = model.Tag.by_name(self.newtagname)
        if tag:
            tag.purge()
        model.Session.commit()
        model.Session.remove()

    def test_setup_ok(self):
        assert 'Packages - Edit' in self.res
        # really want to check it is in the form ...
        assert self.editpkg.notes in self.res

    def test_edit(self):
        new_title = 'A Short Description of this Package'
        newurl = 'http://www.editpkgnewurl.com'
        new_download_url = newurl + '/download/'
        newlicense = 'Non-OKD Compliant::Other'
        newversion = '0.9b'
        fv = self.res.forms[0]
        fv['title'] =  new_title
        fv['url'] =  newurl
        fv['download_url'] =  new_download_url
        fv['licenses'] =  newlicense
        fv['version'] = newversion
        res = fv.submit('commit')
        # get redirected ...
        res = res.follow()
        print str(self.res)
        assert 'Packages - %s' % self.editpkg_name in res
        pkg = model.Package.by_name(self.editpkg.name)
        assert pkg.title == new_title 
        assert pkg.url == newurl
        assert pkg.download_url == new_download_url
        assert pkg.version == newversion
        licenses = [ pkg.license.name ]
        assert newlicense in licenses

    def test_edit_2(self):
        # testing tag updating
        newtags = [self.newtagname]
        tagvalues = ' '.join(newtags)
        fv = self.res.forms[0]
        fv['tags'] =  tagvalues
        exp_log_message = 'test_edit_2: making some changes'
        fv['log_message'] =  exp_log_message
        res = fv.submit('commit')
        # get redirected ...
        res = res.follow()
        print str(res)
        assert 'Packages - %s' % self.editpkg_name in res
        pkg = model.Package.by_name(self.editpkg.name)
        assert len(pkg.tags) == 1
        outtags = [ tag.name for tag in pkg.tags ]
        for tag in newtags:
            assert tag in outtags 
        rev = model.Revision.youngest()
        assert rev.author == 'Unknown IP Address'
        assert rev.message == exp_log_message

    def test_edit_preview(self):
        newurl = 'www.editpkgnewurl.com'
        newnotes = '''
### A title

Hello world.
'''
        fv = self.res.forms[0]
        fv['url'] =  newurl
        fv['notes'] =  newnotes
        res = fv.submit('preview')
        print str(res)
        assert 'Packages - Edit' in res
        assert 'Preview' in res


class TestPackageControllerNew(TestController2):
    pkgname = u'testpkg'
    pkgtitle = u'mytesttitle'

    @classmethod
    def teardown_class(self):
        model.Session.remove()
        pkg = model.Package.by_name(self.pkgname)
        if pkg:
            pkg.purge()
        model.Session.commit()
        model.Session.remove()

    def test_new(self):
        # TODO: test creating a package with an existing name results in error
        offset = url_for(controller='package', action='new')
        res = self.app.get(offset)
        assert 'Packages - New' in res
        print res
        fv = res.forms[0]
        fv['name'] = self.pkgname
        fv['title'] = self.pkgtitle
        res = fv.submit('preview')
        assert 'Preview' in res
        fv = res.forms[0]
        res = fv.submit('commit', status=[302])
        res = res.follow()
        assert 'Packages - %s' % self.pkgname in res, res
        pkg = model.Package.by_name(self.pkgname)
        assert pkg.name == self.pkgname
        assert pkg.title == self.pkgtitle
        # for some reason environ['REMOTE_ADDR'] is undefined
        rev = model.Revision.youngest()
        assert rev.author == 'Unknown IP Address'
        # TODO: reinstate once fixed in code
        exp_log_message = 'Creating package %s' % self.pkgname
        # assert rev.message == exp_log_message

    def test_new_bad_name(self):
        offset = url_for(controller='package', action='new')
        res = self.app.get(offset)
        assert 'Packages - New' in res
        fv = res.forms[0]
        # should result in error as need >= 2 chars
        fv['name'] = 'a'
        res = fv.submit('commit')
        assert 'Error' in res, res
        assert 'Enter a value at least 2 characters long' in res, res

