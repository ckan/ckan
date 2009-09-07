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
        res = res.click('Register a New Package')
        assert 'Packages - New' in res

    def test_read(self):
        name = u'annakarenina'
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
        self._check_search_results(res, 'anna', ['1 package found', 'annakarenina'] )
        self._check_search_results(res, 'war', ['1 package found', 'warandpeace'] )
        self._check_search_results(res, 'a', ['2 packages found', 'warandpeace', 'annakarenina'] )
        self._check_search_results(res, 'n', ['2 packages found', 'warandpeace', 'annakarenina'] )
        self._check_search_results(res, '', ['0 packages found'] )
        self._check_search_results(res, 'z', ['0 packages found'] )
        self._check_search_results(res, '"A Novel By Tolstoy"', ['1 package found'] )
        self._check_search_results(res, 'title:Novel', ['1 package found'] )
        self._check_search_results(res, 'title:peace', ['0 packages found'] )
        self._check_search_results(res, 'name:peace', ['1 package found'] )

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
        self.editpkg.notes = u'Some notes'

        model.Session.commit()
        self.pkgid = self.editpkg.id
        model.Session.remove()
        offset = url_for(controller='package', action='edit', id=self.editpkg.name)
        self.res = self.app.get(offset)
        self.newtagname = u'russian'

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
        new_title = u'A Short Description of this Package'
        newurl = u'http://www.editpkgnewurl.com'
        new_download_url = newurl + u'/download/'
        newlicense = u'Non-OKD Compliant::Other'
        newlicenseid = model.License.by_name(newlicense).id
        newversion = u'0.9b'
        fv = self.res.forms[0]
        prefix = 'Package-%s-' % self.pkgid
        fv[prefix + 'title'] =  new_title
        fv[prefix + 'url'] =  newurl
        fv[prefix + 'download_url'] =  new_download_url
        fv[prefix + 'license_id'] =  newlicenseid
        fv[prefix + 'version'] = newversion
        res = fv.submit('commit')
        # get redirected ...
        res = res.follow()
        assert 'Packages - %s' % self.editpkg_name in res, res
        pkg = model.Package.by_name(self.editpkg.name)
        assert pkg.title == new_title 
        assert pkg.url == newurl
        assert pkg.download_url == new_download_url
        assert pkg.version == newversion
        assert newlicense == pkg.license.name

    def test_edit_2(self):
        # testing tag updating
        newtags = [self.newtagname]
        tagvalues = ' '.join(newtags)
        fv = self.res.forms[0]
        prefix = 'Package-%s-' % self.pkgid
        fv[prefix + 'tags'] =  tagvalues
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
        prefix = 'Package-%s-' % self.pkgid
        fv[prefix + 'url'] =  newurl
        fv[prefix + 'notes'] =  newnotes
        res = fv.submit('preview')
        print str(res)
        assert 'Packages - Edit' in res
        assert 'Preview' in res

    def test_edit_bad_name(self):
        fv = self.res.forms[0]
        prefix = 'Package-%s-' % self.pkgid
        fv[prefix + 'name'] = u'a' # invalid name
        res = fv.submit('commit')
        assert 'Error' in res, res
        assert 'Package name must be at least 2 characters long' in res, res
        # Ensure there is an error at the top of the form and by the field
        assert 'class="form-errors"' in res, res
        assert 'class="field_error"' in res, res

    def test_edit_all_fields(self):
        # Create new item
        rev = model.repo.new_revision()
        pkg_name = u'new_editpkgtest'
        pkg = model.Package(name=pkg_name)
        pkg.title = u'This is a Test Title'
        pkg.url = u'editpkgurl.com'
        pkg.download_url = u'editpkgurl2.com'
        pkg.notes= u'this is editpkg'
        pkg.version = u'2.2'
        pkg.tags = [model.Tag(name=u'one'), model.Tag(name=u'two')]
        tags_txt = ' '.join([tag.name for tag in pkg.tags])
        pkg.license = model.License.byName(u'OKD Compliant::Other')
        
        model.Session.commit()
#        model.Session.remove()

        offset = url_for(controller='package', action='edit', id=pkg.name)
        res = self.app.get(offset)
        assert 'Packages - Edit' in res
        
        # Check form is correctly filled
        prefix = 'Package-%s-' % pkg.id
        assert 'name="%sname" size="40" type="text" value="%s"' % (prefix, pkg.name) in res, res
        assert 'name="%stitle" size="40" type="text" value="%s"' % (prefix, pkg.title) in res, res
        assert 'name="%sversion" size="40" type="text" value="%s"' % (prefix, pkg.version) in res, res
        assert 'name="%surl" size="40" type="text" value="%s"' % (prefix, pkg.url) in res, res
        assert 'name="%sdownload_url" size="40" type="text" value="%s"' % (prefix, pkg.download_url) in res, res
        assert '<textarea cols="60" id="%snotes" name="%snotes" rows="15">%s</textarea>' % (prefix, prefix, pkg.notes) in res, res
        license_html = '<option value="%s" selected>%s' % (pkg.license_id, pkg.license.name)
        assert license_html in res, str(res) + license_html
        tags_html = 'name="%stags" size="60" type="text" value="%s"' % (prefix, tags_txt)
        assert tags_html in res, str(res) + tags_html

        # Amend form
        name = u'test_name'
        title = u'Test Title'
        version = u'1.1'
        url = u'http://something.com/somewhere.zip'
        download_url = u'http://something.com/somewhere-else.zip'
        notes = u'Very important'
        license_id = 4
        license = u'OKD Compliant::Creative Commons CCZero'
        tags = (u'tag1', u'tag2', u'tag3')
        tags_txt = u' '.join(tags)
        assert not model.Package.by_name(name)
        fv = res.forms[0]
        prefix = 'Package-%s-' % pkg.id
        fv[prefix+'name'] = name
        fv[prefix+'title'] = title
        fv[prefix+'version'] = version
        fv[prefix+'url'] = url
        fv[prefix+'download_url'] = download_url
        fv[prefix+'notes'] = notes
        fv[prefix+'license_id'] = license_id
        fv[prefix+'tags'] = tags_txt
        res = fv.submit('preview')
        assert not 'Error' in res, res

        # Check preview is correct
        res1 = str(res).replace('</strong>', '')
        assert 'Preview' in res
        assert 'Title: %s' % str(title) in res1, res
        assert 'Version: %s' % str(version) in res1, res
        assert 'Url: <a href="%s">' % str(url) in res1, res
        assert 'Download Url: <a href="%s">' % str(download_url) in res1, res
        assert '<p>%s' % str(notes) in res1, res
        assert 'Licenses: %s' % str(license) in res1, res
        tags_html_list = ['        <a href="/tag/read/%s">%s</a>' % (str(tag), str(tag)) for tag in tags]
        tags_html = '\n'.join(tags_html_list)
        assert 'Tags:\n%s' % tags_html in res1, res1 + tags_html

        # Check form is correctly filled
        assert 'name="%stitle" size="40" type="text" value="%s"' % (prefix, title) in res, res
        assert 'name="%sversion" size="40" type="text" value="%s"' % (prefix, version) in res, res
        assert 'name="%surl" size="40" type="text" value="%s"' % (prefix, url) in res, res
        assert 'name="%sdownload_url" size="40" type="text" value="%s"' % (prefix, download_url) in res, res
        assert '<textarea cols="60" id="%snotes" name="%snotes" rows="15">%s</textarea>' % (prefix, prefix, notes) in res, res
        license_html = '<option value="%s" selected>%s' % (license_id, license)
        assert license_html in res, str(res) + license_html
        assert 'name="%stags" size="60" type="text" value="%s"' % (prefix, tags_txt) in res, res

        res = fv.submit('commit')
        assert not 'Error' in res, res
        res = res.follow()
        res1 = str(res).replace('</strong>', '')
        assert 'Packages - %s' % str(name) in res1, res1
        assert 'Package: %s' % str(name) in res1, res1
        assert 'Title: %s' % str(title) in res1, res1
        assert 'Version: %s' % str(version) in res1, res1
        assert 'Url: <a href="%s">' % str(url) in res1, res
        assert 'Download Url: <a href="%s">' % str(download_url) in res1, res
        assert '<p>%s' % str(notes) in res1, res1
        assert 'Licenses: %s' % str(license) in res1, res1
        assert 'Tags:\n%s' % tags_html in res1, res1 + tags_html
        pkg = model.Package.by_name(name)
        assert pkg.name == name
        assert pkg.title == title
        assert pkg.version == version
        assert pkg.url == url
        assert pkg.download_url == download_url
        assert pkg.notes == notes
        assert pkg.license_id == license_id
        saved_tagnames = [str(tag.name) for tag in pkg.tags]
        assert saved_tagnames == list(tags)

        # for some reason environ['REMOTE_ADDR'] is undefined
        rev = model.Revision.youngest()
        assert rev.author == 'Unknown IP Address'
        # TODO: reinstate once fixed in code
        exp_log_message = u'Creating package %s' % name
        # assert rev.message == exp_log_message


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
        assert not model.Package.by_name(u'annakarenina')
        offset = url_for(controller='package', action='new')
        res = self.app.get(offset)
        assert 'Packages - New' in res
        fv = res.forms[0]
        prefix = 'Package--'
        fv[prefix + 'name'] = 'annakarenina'
        res = fv.submit('commit')
        assert not 'Error' in res, res

    def test_new_all_fields(self):
        name = u'test_name2'
        title = u'Test Title'
        version = u'1.1'
        url = u'http://something.com/somewhere.zip'
        download_url = u'http://something.com/somewhere-else.zip'
        notes = u'Very important'
        license_id = 4
        license = u'OKD Compliant::Creative Commons CCZero'
        tags = (u'tag1', u'tag2', u'tag3')
        tags_txt = u' '.join(tags)
        assert not model.Package.by_name(name)
        offset = url_for(controller='package', action='new')
        res = self.app.get(offset)
        assert 'Packages - New' in res
        fv = res.forms[0]
        prefix = 'Package--'
        fv[prefix+'name'] = name
        fv[prefix+'title'] = title
        fv[prefix+'version'] = version
        fv[prefix+'url'] = url
        fv[prefix+'download_url'] = download_url
        fv[prefix+'notes'] = notes
        fv[prefix+'license_id'] = license_id
        fv[prefix+'tags'] = tags_txt
        res = fv.submit('preview')
        assert not 'Error' in res, res

        # Check preview is correct
        res1 = str(res).replace('</strong>', '')
        assert 'Preview' in res
#        import pdb; pdb.set_trace()
        assert 'Title: %s' % str(title) in res1, res
        assert 'Version: %s' % str(version) in res1, res
        assert 'Url: <a href="%s">' % str(url) in res1, res
        assert 'Download Url: <a href="%s">' % str(download_url) in res1, res
        assert '<p>%s' % str(notes) in res1, res
        assert 'Licenses: %s' % str(license) in res1, res
        tags_html_list = ['        <a href="/tag/read/%s">%s</a>' % (str(tag), str(tag)) for tag in tags]
        tags_html = '\n'.join(tags_html_list)
        assert 'Tags:\n%s' % tags_html in res1, res1 + tags_html

        # Check form is correctly filled
        assert 'name="Package--title" size="40" type="text" value="%s"' % title in res, res
        assert 'name="Package--version" size="40" type="text" value="%s"' % version in res, res
        assert 'name="Package--url" size="40" type="text" value="%s"' % url in res, res
        assert 'name="Package--download_url" size="40" type="text" value="%s"' % download_url in res, res
        assert '<textarea cols="60" id="Package--notes" name="Package--notes" rows="15">%s</textarea>' % notes in res, res
        license_html = '<option value="%s" selected>%s' % (license_id, license)
        assert license_html in res, str(res) + license_html
        assert 'name="Package--tags" size="60" type="text" value="%s"' % tags_txt in res, res

        res = fv.submit('commit')
        assert not 'Error' in res, res
        res = res.follow()
        res1 = str(res).replace('</strong>', '')
        assert 'Packages - %s' % str(name) in res1, res1
        assert 'Package: %s' % str(name) in res1, res1
        assert 'Title: %s' % str(title) in res1, res1
        assert 'Version: %s' % str(version) in res1, res1
        assert 'Url: <a href="%s">' % str(url) in res1, res
        assert 'Download Url: <a href="%s">' % str(download_url) in res1, res
        assert '<p>%s' % str(notes) in res1, res1
        assert 'Licenses: %s' % str(license) in res1, res1
        assert 'Tags:\n%s' % str(tags_html) in res1, res1 + tags_html
        pkg = model.Package.by_name(name)
        assert pkg.name == name
        assert pkg.title == title
        assert pkg.version == version
        assert pkg.url == url
        assert pkg.download_url == download_url
        assert pkg.notes == notes
        assert pkg.license_id == license_id
        saved_tagnames = [str(tag.name) for tag in pkg.tags]
        assert saved_tagnames == list(tags)

        # for some reason environ['REMOTE_ADDR'] is undefined
        rev = model.Revision.youngest()
        assert rev.author == 'Unknown IP Address'
        # TODO: reinstate once fixed in code
        exp_log_message = u'Creating package %s' % name
        # assert rev.message == exp_log_message

    def test_new_existing_name(self):
        # test creating a package with an existing name results in error'
        # create initial package
        assert not model.Package.by_name(self.pkgname)
        offset = url_for(controller='package', action='new')
        res = self.app.get(offset)
        assert 'Packages - New' in res
        fv = res.forms[0]
        prefix = 'Package--'
        fv[prefix + 'name'] = self.pkgname
        res = fv.submit('commit')
        assert not 'Error' in res, res
        assert model.Package.by_name(self.pkgname)
        # create duplicate package
        res = self.app.get(offset)
        assert 'Packages - New' in res
        fv = res.forms[0]
        fv[prefix+'name'] = self.pkgname
        fv[prefix+'title'] = self.pkgtitle
        res = fv.submit('preview')
        assert 'Preview' in res
        fv = res.forms[0]
        res = fv.submit('commit')
        assert 'Error' in res, res
        assert 'Package name already exists in database' in res, res
        # Ensure there is an error at the top of the form and by the field
        assert 'class="form-errors"' in res, res
        assert 'class="field_error"' in res, res
        
    def test_new_bad_name(self):
        offset = url_for(controller='package', action='new')
        res = self.app.get(offset)
        assert 'Packages - New' in res
        fv = res.forms[0]
        prefix = 'Package--'
        # should result in error as need >= 2 chars
        fv[prefix + 'name'] = 'a'
        fv[prefix + 'title'] = 'A Test Package'
        fv[prefix + 'tags'] = 'test tags'
        res = fv.submit('commit')
        assert 'Error' in res, res
        assert 'Package name must be at least 2 characters long' in res, res
        # Ensure there is an error at the top of the form and by the field
        assert 'class="form-errors"' in res, res
        assert 'class="field_error"' in res, res
        # Ensure fields are prefilled
        assert 'value="A Test Package"' in res, res
        assert 'value="test tags"' in res, res

