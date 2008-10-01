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

class TestPackageControllerUpdate(TestController2):

    def test_update(self):
        offset = url_for(controller='package', action='update')
        try:
            res = self.app.get(offset)
        except AppError, inst:
            error = str(inst)
        else:
            assert False, "Request didn't product an error: %s." % offset
        assert 'Packages - Updating' in error
        assert 'There was an error' in error


class TestPackageControllerEdit(TestController2):

    def setup_method(self, method):
        rev = model.new_revision()
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
        fv = self.res.forms[0]
        fv['title'] =  new_title
        fv['url'] =  newurl
        fv['download_url'] =  new_download_url
        fv['licenses'] =  newlicense
        res = fv.submit('commit')
        # get redirected ...
        res = res.follow()
        print str(self.res)
        assert 'Packages - %s' % self.editpkg_name in res
        pkg = model.Package.by_name(self.editpkg.name)
        assert pkg.title == new_title 
        assert pkg.url == newurl
        assert pkg.download_url == new_download_url
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

    def teardown_class(self):
        # 2008-10-01 model.Sessionremove is crucial here
        # without it pkg is not correctly torn down due to weird interference
        # between test_create and test_new (running test_new alone everything
        # is ok ...)
        model.Session.remove()
        pkg = model.Package.by_name(self.pkgname)
        if pkg:
            pkg.purge()
        model.Session.commit()
        model.Session.remove()

    def test_create(self):
        offset = url_for(controller='package', action='create', id=None)
        try:
            res = self.app.get(offset)
        except AppError, inst:
            error = str(inst)
        else:
            assert False, "Request didn't product an error: %s." % offset
        assert "400 Bad Request -- Missing name request parameter." in error

    def test_new(self):
        # TODO: test creating a package with an existing name results in error
        offset = url_for(controller='package', action='new')
        res = self.app.get(offset)
        assert 'Packages - New' in res
        fv = res.forms[0]
        fv['name'] = self.pkgname
        res = fv.submit(status=[302])
        res = res.follow()
        assert 'Packages - Edit' in res
        rev = model.Revision.youngest()
        pkg = model.Package.by_name(self.pkgname)
        assert pkg.name == self.pkgname
        # for some reason environ['REMOTE_ADDR'] is undefined when using twill
        assert rev.author == 'Unknown IP Address'
        exp_log_message = 'Creating package %s' % self.pkgname
        assert rev.message == exp_log_message

