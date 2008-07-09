from ckan.tests import *
import ckan.models

import cgi
from paste.fixture import AppError

class TestPackageController(TestController2):

    def setup_class(self):
        repo = ckan.models.repo
        rev = repo.youngest_revision()
        self.anna = rev.model.packages.get('annakarenina')

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
        name = self.anna.name
        offset = url_for(controller='package', action='read', id=name)
        res = self.app.get(offset)
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
        # super(TestPackageControllerEdit, self).setup_method(method)
        txn = ckan.models.repo.begin_transaction()
        self.editpkg_name = 'editpkgtest'
        self.editpkg = txn.model.packages.create(name=self.editpkg_name)
        self.editpkg.url = 'editpkgurl.com'
        self.editpkg.notes='this is editpkg'
        txn.commit()
        offset = url_for(controller='package', action='edit', id=self.editpkg.name)
        self.res = self.app.get(offset)

    def teardown_method(self, method):
        # super(TestPackageControllerEdit, self).teardown_method(method)
        rev = ckan.models.repo.youngest_revision()
        rev.model.packages.purge(self.editpkg.name)
        # if method == 'test_edit_2':
            # self._teardown_test_edit2()

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
        rev = ckan.models.repo.youngest_revision()
        pkg = rev.model.packages.get(self.editpkg.name)
        assert pkg.title == new_title 
        assert pkg.url == newurl
        assert pkg.download_url == new_download_url
        licenses = [ pkg.license.name ]
        assert newlicense in licenses

    def test_edit_2(self):
        # testing tag updating
        newtags = ['russian']
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
        rev = ckan.models.repo.youngest_revision()
        pkg = rev.model.packages.get(self.editpkg.name)
        assert len(pkg.tags.list()) == 1
        outtags = [ pkg2tag.tag.name for pkg2tag in pkg.tags ]
        for tag in newtags:
            assert tag in outtags 
        # for some reason environ['REMOTE_ADDR'] is undefined when using twill
        assert rev.author == 'Unknown IP Address'
        assert rev.log_message == exp_log_message

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

    def setup_class(self):
        self.testvalues = { 'name' : 'testpkg' }

    def teardown_class(self):
        rev = ckan.models.repo.youngest_revision()
        try:
            rev.model.packages.purge(self.testvalues['name'])
        except:
            pass

    def test_create(self):
        offset = url_for(controller='package', action='create')
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
        fv['name'] = self.testvalues['name']
        res = fv.submit(status=[302])
        res = res.follow()
        assert 'Packages - Edit' in res
        rev = ckan.models.repo.youngest_revision()
        pkg = rev.model.packages.get(self.testvalues['name'])
        assert pkg.name == self.testvalues['name']
        # for some reason environ['REMOTE_ADDR'] is undefined when using twill
        assert rev.author == 'Unknown IP Address'
        exp_log_message = 'Creating package %s' % self.testvalues['name']
        assert rev.log_message == exp_log_message

