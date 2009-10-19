from ckan.tests import *
import ckan.model as model

import cgi
from paste.fixture import AppError

existing_extra_html = ('<label class="field_opt" for="Package-%(package_id)s-extras-%(key)s">%(capitalized_key)s</label>', '<input id="Package-%(package_id)s-extras-%(key)s" name="Package-%(package_id)s-extras-%(key)s" size="20" type="text" value="%(value)s">')

class TestPackageController(TestController):

    @classmethod
    def setup_class(self):
        CreateTestData.create()

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()

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
        assert 'Groups:' in res
        assert 'david' in res
        assert 'roger' in res
        assert 'State:' not in res
        assert 'Genre:' in res
        assert 'romantic novel' in res
        assert 'Original media:' in res
        assert 'book' in res

    def test_read_as_admin(self):
        name = u'annakarenina'
        offset = url_for(controller='package', action='read', id=name)
        res = self.app.get(offset, extra_environ={'REMOTE_USER':'annafan'})
        assert 'State:' in res, res

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
        self._check_search_results(res, 'groups:david', ['2 packages found'] )
        self._check_search_results(res, 'groups:roger', ['1 package found'] )
        self._check_search_results(res, 'groups:lenny', ['0 packages found'] )

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

class TestPackageControllerEdit(TestController):
    def setup_method(self, method):
        self.setUp()

    def setUp(self):
        rev = model.repo.new_revision()
        self.editpkg_name = u'editpkgtest'
        editpkg = model.Package(name=self.editpkg_name)
        editpkg.url = u'editpkgurl.com'
        editpkg.notes = u'Some notes'
        model.User(name=u'testadmin')
        model.repo.commit_and_remove()

        editpkg = model.Package.by_name(self.editpkg_name)
        admin = model.User.by_name(u'testadmin')
        model.setup_default_user_roles(editpkg, [admin])
        self.pkgid = editpkg.id
        offset = url_for(controller='package', action='edit', id=self.editpkg_name)
        self.res = self.app.get(offset)
        self.newtagname = u'russian'
        model.repo.commit_and_remove()

        self.editpkg = model.Package.by_name(self.editpkg_name)
        self.admin = model.User.by_name(u'testadmin')

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
        model.Session.remove()
        offset = url_for(controller='package', action='read', id=self.editpkg_name)
        res = self.app.get(offset)
        assert 'Packages - %s' % self.editpkg_name in res, res
        pkg = model.Package.by_name(self.editpkg.name)
        assert pkg.title == new_title 
        assert pkg.url == newurl
        assert pkg.download_url == new_download_url
        assert pkg.version == newversion
        assert newlicense == pkg.license.name

    def test_edit_2_not_groups(self):
        # not allowed to edit groups for now
        prefix = 'Package-%s-' % self.pkgid
        fv = self.res.forms[0]
        assert not fv.fields.has_key(prefix + 'groups')
        
    def test_edit_2_tags_and_groups(self):
        # testing tag updating
        newtags = [self.newtagname]
        tagvalues = ' '.join(newtags)
##        newgroups = [u'lenny']
##        groupvalues = ' '.join(newgroups)
        fv = self.res.forms[0]
        prefix = 'Package-%s-' % self.pkgid
        fv[prefix + 'tags'] =  tagvalues
##        fv[prefix + 'groups'] =  groupvalues
        exp_log_message = 'test_edit_2: making some changes'
        fv['log_message'] =  exp_log_message
        res = fv.submit('commit')
        # get redirected ...
        res = res.follow()
        print str(res)
        assert 'Packages - %s' % self.editpkg_name in res
        pkg = model.Package.by_name(self.editpkg.name)
        assert len(pkg.tags) == 1
##        assert len(pkg.groups) == 1
        outtags = [ tag.name for tag in pkg.tags ]
        for tag in newtags:
            assert tag in outtags 
##        outgroups = [ group.name for group in pkg.groups ]
##        for group in newgroups:
##            assert group in outgroups 
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
        assert 'Name must be at least 2 characters long' in res, res
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
        pkg.state = model.State.query.filter_by(name='deleted').one()
        tags_txt = ' '.join([tag.name for tag in pkg.tags])
        pkg.license = model.License.byName(u'OKD Compliant::Other')
        extras = {'key1':'value1', 'key2':'value2', 'key3':'value3'}
        for key, value in extras.items():
            pkg.extras[unicode(key)] = unicode(value)
        model.repo.commit_and_remove()

        pkg = model.Package.by_name(pkg_name)
        model.setup_default_user_roles(pkg, [self.admin])

        offset = url_for(controller='package', action='edit', id=pkg.name)
        res = self.app.get(offset, status=200, extra_environ={'REMOTE_USER':'testadmin'})
        assert 'Packages - Edit' in res, res
        
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
        state_html = '<option value="%s" selected>%s' % (pkg.state.id, pkg.state.name)
        assert state_html in res, str(res) + state_html
        for key, value in extras.items():
            for html in existing_extra_html:
                extras_html = html % {'package_id':pkg.id, 'key':key, 'capitalized_key':key.capitalize(), 'value':value}
                assert extras_html in res, str(res) + extras_html

        # Amend form
        name = u'test_name'
        title = u'Test Title'
        version = u'1.1'
        url = u'http://something.com/somewhere.zip'
        download_url = u'http://something.com/somewhere-else.zip'
        notes = u'Very important'
        license_id = 4
        license = u'OKD Compliant::Creative Commons CCZero'
        state = model.State.query.filter_by(name='active').one()
        tags = (u'tag1', u'tag2', u'tag3')
        tags_txt = u' '.join(tags)
        extra_changed = 'key1', 'value1 CHANGED'
        extra_new = 'newkey', 'newvalue'
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
        fv[prefix+'state_id'] = state.id
        fv[prefix+'extras-%s' % extra_changed[0]] = extra_changed[1]
        fv[prefix+'extras-newfield0-key'] = extra_new[0]
        fv[prefix+'extras-newfield0-value'] = extra_new[1]
        fv[prefix+'extras-key3-checkbox'] = True
        res = fv.submit('preview', extra_environ={'REMOTE_USER':'testadmin'})
        assert not 'Error' in res, res

        # Check preview is correct
        res1 = str(res).replace('</strong>', '')
        assert 'Preview' in res, res
        assert 'Title: %s' % str(title) in res1, res
        assert 'Version: %s' % str(version) in res1, res
        assert 'Url: <a href="%s">' % str(url) in res1, res
        assert 'Download Url: <a href="%s">' % str(download_url) in res1, res
        assert '<p>%s' % str(notes) in res1, res
        assert 'Licenses: %s' % str(license) in res1, res
        tags_html_list = ['        <a href="/tag/read/%s">%s</a>' % (str(tag), str(tag)) for tag in tags]
        tags_html = '\n'.join(tags_html_list)
        assert 'Tags:\n%s' % tags_html in res1, res1 + tags_html
##        groups_html_list = ['        <a href="/group/read/%s">%s</a>' % (str(group), str(group)) for group in groups]
##        groups_html = '\n'.join(groups_html_list)
        groups_html = ''
        assert 'Groups:\n%s' % groups_html in res1, res1 + groups_html
        assert 'State: %s' % str(state.name) in res1, res
        assert 'Extras:' in res1, res
        current_extras = (('key2', extras['key2']),
                          extra_changed,
                          extra_new)
        deleted_extras = [('key3', extras['key3'])]
        for key, value in current_extras:
            extras_html = '%(key)s: %(value)s' % {'key':key.capitalize(), 'value':value}
            assert extras_html in res1, str(res) + extras_html
        for key, value in deleted_extras:
            extras_html = '%(key)s: %(value)s' % {'key':key.capitalize(), 'value':value}
            assert extras_html not in res1, str(res) + extras_html
        assert '<li><strong>:</strong> </li>' not in res, res

        # Check form is correctly filled
        assert 'name="%stitle" size="40" type="text" value="%s"' % (prefix, title) in res, res
        assert 'name="%sversion" size="40" type="text" value="%s"' % (prefix, version) in res, res
        assert 'name="%surl" size="40" type="text" value="%s"' % (prefix, url) in res, res
        assert 'name="%sdownload_url" size="40" type="text" value="%s"' % (prefix, download_url) in res, res
        assert '<textarea cols="60" id="%snotes" name="%snotes" rows="15">%s</textarea>' % (prefix, prefix, notes) in res, res
        license_html = '<option value="%s" selected>%s' % (license_id, license)
        assert license_html in res, str(res) + license_html
        assert 'name="%stags" size="60" type="text" value="%s"' % (prefix, tags_txt) in res, res
        state_html = '<option value="%s" selected>%s' % (state.id, state.name)
        assert state_html in res, str(res) + state_html
        for key, value in current_extras:
            for html in existing_extra_html:
                extras_html = html % {'package_id':pkg.id, 'key':key, 'capitalized_key':key.capitalize(), 'value':value}
                assert extras_html in res, str(res) + extras_html
        for key, value in deleted_extras:
            for html in existing_extra_html:
                extras_html = html % {'package_id':pkg.id, 'key':key, 'capitalized_key':key.capitalize(), 'value':value}
                assert extras_html not in res, str(res) + extras_html

        # Submit
        res = fv.submit('commit', extra_environ={'REMOTE_USER':'testadmin'})

        # Check package page
        assert not 'Error' in res, res
        res = res.follow(extra_environ={'REMOTE_USER':'testadmin'})
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
        assert 'Groups:\n%s' % groups_html in res1, res1 + groups_html
        assert 'State: %s' % str(state.name) in res1, res1
        for key, value in current_extras:
            extras_html = '%(key)s: %(value)s' % {'key':key.capitalize(), 'value':value}
            assert extras_html in res1, str(res) + extras_html

        # Check package object
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
        assert pkg.state_id == state.id
        assert len(pkg.extras) == len(current_extras)
        for key, value in current_extras:
            assert pkg.extras[key] == value

        # for some reason environ['REMOTE_ADDR'] is undefined
        rev = model.Revision.youngest()
        assert rev.author == 'testadmin', rev.author
        # TODO: reinstate once fixed in code
        exp_log_message = u'Creating package %s' % name
        #assert rev.message == exp_log_message


class TestPackageControllerNew(TestController):
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
##        groups = (u'group1', u'group2', u'group3')
##        groups_txt = u' '.join(groups)
        extras = {'key1':'value1', 'key2':'value2', 'key3':'value3'}
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
##        fv[prefix+'groups'] = groups_txt
        for i, extra in enumerate(extras.items()):
            fv[prefix+'extras-newfield%s-key' % i] = extra[0]
            fv[prefix+'extras-newfield%s-value' % i] = extra[1]
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
##        groups_html_list = ['        <a href="/group/read/%s">%s</a>' % (str(group), str(group)) for group in groups]
##        groups_html = '\n'.join(groups_html_list)
        groups_html = ''
        assert 'Groups:\n%s' % groups_html in res1, res1 + groups_html
        assert 'Extras:' in res1, res
        current_extras = extras.items()
        for key, value in current_extras:
            extras_html = '%(key)s: %(value)s' % {'key':key.capitalize(), 'value':value}
            assert extras_html in res1, str(res) + extras_html
        assert '<li><strong>:</strong> </li>' not in res, res

        # Check form is correctly filled
        assert 'name="Package--title" size="40" type="text" value="%s"' % title in res, res
        assert 'name="Package--version" size="40" type="text" value="%s"' % version in res, res
        assert 'name="Package--url" size="40" type="text" value="%s"' % url in res, res
        assert 'name="Package--download_url" size="40" type="text" value="%s"' % download_url in res, res
        assert '<textarea cols="60" id="Package--notes" name="Package--notes" rows="15">%s</textarea>' % notes in res, res
        license_html = '<option value="%s" selected>%s' % (license_id, license)
        assert license_html in res, str(res) + license_html
        assert 'name="Package--tags" size="60" type="text" value="%s"' % tags_txt in res, res
##        assert 'name="Package--groups" size="60" type="text" value="%s"' % groups_txt in res, res
        for key, value in current_extras:
            for html in existing_extra_html:
                extras_html = html % {'package_id':'', 'key':key, 'capitalized_key':key.capitalize(), 'value':value}
                assert extras_html in res, str(res) + extras_html

        # Submit
        res = fv.submit('commit')

        # Check package page
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
        assert 'Groups:\n%s' % str(groups_html) in res1, res1 + groups_html
        for key, value in current_extras:
            extras_html = '%(key)s: %(value)s' % {'key':key.capitalize(), 'value':value}
            assert extras_html in res1, str(res) + extras_html

        # Check package object
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
        saved_groupnames = [str(group.name) for group in pkg.groups]
        assert len(pkg.extras) == len(current_extras)
        for key, value in current_extras:
            assert pkg.extras[key] == value

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
#        fv[prefix + 'groups'] = 'test groups'
        res = fv.submit('commit')
        assert 'Error' in res, res
        assert 'Name must be at least 2 characters long' in res, res
        # Ensure there is an error at the top of the form and by the field
        assert 'class="form-errors"' in res, res
        assert 'class="field_error"' in res, res
        # Ensure fields are prefilled
        assert 'value="A Test Package"' in res, res
        assert 'value="test tags"' in res, res
#        assert 'value="test groups"' in res, res

class TestNonActivePackages(TestController):

    @classmethod
    def setup_class(self):
        CreateTestData.create()
        self.non_active_name = u'test_nonactive'
        model.Package(name=self.non_active_name)
        model.repo.new_revision()
        model.repo.commit_and_remove()

        pkg = model.Package.query.filter_by(name=self.non_active_name).one()
        admin = model.User.by_name(u'joeadmin')
        model.setup_default_user_roles(pkg, [admin])
        
        pkg = model.Package.query.filter_by(name=self.non_active_name).one()
        pkg.delete() # becomes non active
        model.repo.new_revision()
        model.repo.commit_and_remove()
        

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()

    def test_list(self):
        offset = url_for(controller='package', action='list')
        res = self.app.get(offset)
        assert 'Packages - List' in res
        assert 'annakarenina' in res
        assert self.non_active_name not in res

    def test_read(self):
        offset = url_for(controller='package', action='read', id=self.non_active_name)
        res = self.app.get(offset, status=[302, 401])


    def test_read_as_admin(self):
        offset = url_for(controller='package', action='read', id=self.non_active_name)
        res = self.app.get(offset, status=200, extra_environ={'REMOTE_USER':'joeadmin'})

    def test_search(self):
        offset = url_for(controller='package', action='search')
        res = self.app.get(offset)
        assert 'Packages - Search' in res
        form = res.forms[0]
        form['q'] =  str(self.non_active_name)
        results_page = form.submit()
        assert 'Packages - Search' in results_page, results_page
        print results_page
        assert '0 packages found' in results_page, (self.non_active_name, results_page)


        
