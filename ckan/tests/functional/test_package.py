import cgi

from paste.fixture import AppError

from ckan.tests import *
import ckan.model as model
from ckan.lib.create_test_data import CreateTestData

existing_extra_html = ('<label class="field_opt" for="Package-%(package_id)s-extras-%(key)s">%(capitalized_key)s</label>', '<input id="Package-%(package_id)s-extras-%(key)s" name="Package-%(package_id)s-extras-%(key)s" size="20" type="text" value="%(value)s">')

package_form=''

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
        assert 'Packages - %s' % name in res
        assert name in res
        assert self.anna.version in res
        assert self.anna.url in res
        assert cgi.escape(self.anna.resources[0].url) in res
        assert self.anna.resources[0].description in res
        assert 'Some test notes' in res
        assert '<strong>Some bolded text.</strong>' in res
        assert 'License:' in res
        assert 'OKD Compliant::' in res
        assert 'russian' in res
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

    def test_read_internal_links(self):
        pkg_name = u'link-test',
        CreateTestData.create_arbitrary([
            {'name':pkg_name,
             'notes':'Decoy link here: decoy:decoy, real links here: package:pkg-1, ' \
                   'tag:tag_1 group:test-group-1.',
             }
            ])
        offset = url_for(controller='package', action='read', id=pkg_name)
        res = self.app.get(offset)
        def check_link(res, controller, id):
            link = '<a href="/%s/read/%s">%s:%s</a>' % (controller, id, controller, id)
            assert link in res, self.main_div(res) + link
        check_link(res, 'package', 'pkg-1')
        check_link(res, 'tag', 'tag_1')
        check_link(res, 'group', 'test-group-1')
        assert 'decoy</a>' not in res, res
        assert 'decoy"' not in res, res

    def test_list(self):
        offset = url_for(controller='package', action='list')
        res = self.app.get(offset)
        assert 'Packages' in res
        name = u'annakarenina'
        title = u'A Novel By Tolstoy'
        assert title in res
        res = res.click(title)
        assert 'Packages - %s' % name in res, res
        assert title in res, res

    def test_search(self):
        offset = url_for(controller='package', action='search')
        res = self.app.get(offset)
        assert 'Search packages' in res
        self._check_search_results(res, 'annakarenina', ['<strong>1</strong>', 'A Novel By Tolstoy'] )
        self._check_search_results(res, 'warandpeace', ['<strong>0</strong>'], only_downloadable=True )
        self._check_search_results(res, 'warandpeace', ['<strong>0</strong>'], only_open=True )
        self._check_search_results(res, 'annakarenina', ['<strong>1</strong>'], only_open=True, only_downloadable=True )

    def _check_search_results(self, page, terms, requireds, only_open=False, only_downloadable=False):
        form = page.forms[0]
        form['q'] = str(terms)
        form['open_only'] = only_open
        form['downloadable_only'] = only_downloadable
        results_page = form.submit()
        assert 'Search packages' in results_page, results_page
        results_page = self.main_div(results_page)
        for required in requireds:
            results_page = self.main_div(results_page)
            assert required in results_page, "%s : %s" % (results_page, required)
    
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
        offset = url_for(controller='package', action='edit', id=self.editpkg_name, package_form=package_form)
        self.res = self.app.get(offset)
        self.newtagnames = [u'russian', u'tolstoy', u'superb']
        model.repo.commit_and_remove()

        self.editpkg = model.Package.by_name(self.editpkg_name)
        self.admin = model.User.by_name(u'testadmin')

    def teardown_method(self, method):
        self.tearDown()

    def tearDown(self):
        pkg = model.Package.by_name(self.editpkg.name)
        if pkg:
            pkg.purge()
        for tagname in self.newtagnames:
            tag = model.Tag.by_name(tagname)
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
        fv[prefix + 'resources-0-url'] =  new_download_url
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
        assert pkg.resources[0].url == new_download_url
        assert pkg.version == newversion
        assert newlicense == pkg.license.name

    def test_edit_2_not_groups(self):
        # not allowed to edit groups for now
        prefix = 'Package-%s-' % self.pkgid
        fv = self.res.forms[0]
        assert not fv.fields.has_key(prefix + 'groups')
        
    def test_edit_2_tags_and_groups(self):
        # testing tag updating
        newtags = self.newtagnames
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
        assert len(pkg.tags) == len(self.newtagnames)
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
        pkg.resources.append(model.PackageResource(url=u'editpkgurl1',
              format=u'plain text', description=u'Full text'))
        pkg.resources.append(model.PackageResource(url=u'editpkgurl2',
              format=u'plain text2', description=u'Full text2'))
        pkg.notes= u'this is editpkg'
        pkg.version = u'2.2'
        pkg.tags = [model.Tag(name=u'one'), model.Tag(name=u'two')]
        pkg.state = model.State.query.filter_by(name='deleted').one()
        tags_txt = ' '.join([tag.name for tag in pkg.tags])
        pkg.license = model.License.by_name(u'OKD Compliant::Other')
        extras = {'key1':'value1', 'key2':'value2', 'key3':'value3'}
        for key, value in extras.items():
            pkg.extras[unicode(key)] = unicode(value)
        model.repo.commit_and_remove()
        pkg = model.Package.by_name(pkg_name)
        model.setup_default_user_roles(pkg, [self.admin])

        # Edit it
        offset = url_for(controller='package', action='edit', id=pkg.name, package_form=package_form)
        res = self.app.get(offset, status=200, extra_environ={'REMOTE_USER':'testadmin'})
        assert 'Packages - Edit' in res, res
        
        # Check form is correctly filled
        prefix = 'Package-%s-' % pkg.id
        assert 'name="%sname" size="40" type="text" value="%s"' % (prefix, pkg.name) in res, res
        assert 'name="%stitle" size="40" type="text" value="%s"' % (prefix, pkg.title) in res, res
        assert 'name="%sversion" size="40" type="text" value="%s"' % (prefix, pkg.version) in res, res
        assert 'name="%surl" size="40" type="text" value="%s"' % (prefix, pkg.url) in res, res
        res_html = 'id="%sresources-0-url" type="text" value="%s"' % (prefix, pkg.resources[0].url)
        assert res_html in res, self.main_div(res) + res_html
        for res_index, resource in enumerate(pkg.resources):
            for res_field in ('url', 'format', 'description'):
                expected_value = getattr(resource, res_field)
                assert 'id="%sresources-%s-%s" type="text" value="%s"' % (prefix, res_index, res_field, expected_value) in res, res
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
        resources = ((u'http://something.com/somewhere-else.xml', u'xml', u'Best'),
                     (u'http://something.com/somewhere-else2.xml', u'xml2', u'Best2'),
#                     (u'http://something.com/somewhere-else3.xml', u'xml3', u'Best3'),
                     )
        notes = u'Very important'
        license_id = 4
        license = u'OKD Compliant::Creative Commons CCZero'
        state = model.State.query.filter_by(name='active').one()
        tags = (u'tag1', u'tag2', u'tag3')
        tags_txt = u' '.join(tags)
        extra_changed = 'key1', 'value1 CHANGED'
        extra_new = 'newkey', 'newvalue'
        log_message = 'This is a comment'
        assert not model.Package.by_name(name)
        fv = res.forms[0]
        prefix = 'Package-%s-' % pkg.id
        fv[prefix+'name'] = name
        fv[prefix+'title'] = title
        fv[prefix+'version'] = version
        fv[prefix+'url'] = url
        for res_index, resource in enumerate(resources):
            for field_index, res_field in enumerate(('url', 'format', 'description')):
                fv[prefix+'resources-%s-%s' % (res_index, res_field)] = resource[field_index]
        fv[prefix+'notes'] = notes
        fv[prefix+'license_id'] = license_id
        fv[prefix+'tags'] = tags_txt
        fv[prefix+'state_id'] = state.id
        fv[prefix+'extras-%s' % extra_changed[0]] = extra_changed[1]
        fv[prefix+'extras-newfield0-key'] = extra_new[0]
        fv[prefix+'extras-newfield0-value'] = extra_new[1]
        fv[prefix+'extras-key3-checkbox'] = True
        fv['log_message'] = log_message
        res = fv.submit('preview', extra_environ={'REMOTE_USER':'testadmin'})
        assert not 'Error' in res, res

        # Check preview is correct
        res1 = str(res).replace('</strong>', '')
        preview =  res1[res1.find('<div id="preview"'):res1.find('<div id="footer">')]
        assert 'Preview' in preview, preview
        assert 'Title: %s' % str(title) in preview, preview
        assert 'Version: %s' % str(version) in preview, preview
        assert 'URL: <a href="%s">' % str(url) in preview, preview
        for res_index, resource in enumerate(resources):
            res_html = '<tr> <td><a href="%s">%s</a></td><td>%s</td><td>%s</td>' % (resource[0], resource[0], resource[1], resource[2]) 
            assert res_html in preview, preview + res_html
        assert '<p>%s' % str(notes) in preview, preview
        assert 'License: %s' % str(license) in preview, preview
        tags_html_list = ['<a href="/tag/read/%s">%s</a>' % (str(tag), str(tag)) for tag in tags]
        tags_html_preview = ' '.join(tags_html_list)
        assert 'Tags: %s' % tags_html_preview in preview, preview + tags_html_preview
        groups_html = ''
#        assert 'Groups:\n%s' % groups_html in preview, preview + groups_html
        assert 'State: %s' % str(state.name) in preview, preview
#        assert 'Extras:' in preview, preview
        current_extras = (('key2', extras['key2']),
                          extra_changed,
                          extra_new)
        deleted_extras = [('key3', extras['key3'])]
        for key, value in current_extras:
            extras_html = '%(key)s: %(value)s' % {'key':key.capitalize(), 'value':value}
            assert extras_html in preview, str(preview) + extras_html
        for key, value in deleted_extras:
            extras_html = '%(key)s: %(value)s' % {'key':key.capitalize(), 'value':value}
            assert extras_html not in preview, str(preview) + extras_html
        assert '<li><strong>:</strong> </li>' not in preview, preview

        # Check form is correctly filled
        assert 'name="%stitle" size="40" type="text" value="%s"' % (prefix, title) in res, res
        assert 'name="%sversion" size="40" type="text" value="%s"' % (prefix, version) in res, res
        assert 'name="%surl" size="40" type="text" value="%s"' % (prefix, url) in res, res
        res_html = 'id="%sresources-0-url" type="text" value="%s"' % (prefix, resources[0][0])
        assert res_html in res, self.main_div(res) + res_html
        for res_index, resource in enumerate(resources):
            for field_index, res_field in enumerate(('url', 'format', 'description')):
                expected_value = resource[field_index]
                assert 'id="%sresources-%s-%s" type="text" value="%s"' % (prefix, res_index, res_field, expected_value) in res, res
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
        assert log_message in res

        # Submit
        res = fv.submit('commit', extra_environ={'REMOTE_USER':'testadmin'})

        # Check package page
        assert not 'Error' in res, res
        res = res.follow(extra_environ={'REMOTE_USER':'testadmin'})
        main_res = self.main_div(res).replace('</strong>', '')
        sidebar = self.sidebar(res)
        res1 = (main_res + sidebar).decode('ascii', 'ignore')
        assert 'Packages - %s' % str(name) in res, res
        assert str(name) in res1, res1
        assert str(title) in res1, res1
        assert str(version) in res1, res1
        assert '<a href="%s">' % str(url).lower() in res1.lower(), res1
        for res_index, resource in enumerate(resources):
            res_html = '<tr><td><a href="%s">%s</a></td><td>%s</td><td>%s</td>' % (resource[0], resource[0], resource[1], resource[2])
            assert res_html in res1, '%s : %s' % (res1, res_html)
        assert str(notes) in res1, res1
        assert str(license) in res1, res1
        for tag_html in tags_html_list:
            assert tag_html in res1, res1
        assert groups_html in res1, res1 + groups_html
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
        for res_index, resource in enumerate(resources):
            for field_index, res_field in enumerate(('url', 'format', 'description')):
                assert getattr(pkg.resources[res_index], res_field) == resource[field_index]
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
        assert rev.message == log_message
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

    def test_new_with_params_1(self):
        offset = url_for(controller='package', action='new',
                url='http://xxx.org', package_form=package_form)
        res = self.app.get(offset)
        form = res.forms[0]
        form['Package--url'].value == 'http://xxx.org/'
        form['Package--name'].value == 'xxx.org'

    def test_new_with_params_2(self):
        offset = url_for(controller='package', action='new',
                url='http://www.xxx.org', package_form=package_form)
        res = self.app.get(offset)
        form = res.forms[0]
        form['Package--name'].value == 'xxx.org'

    def test_new_without_resource(self):
        # new package
        prefix = 'Package--'
        name = u'test_no_res'
        offset = url_for(controller='package', action='new', package_form=package_form)
        res = self.app.get(offset)
        fv = res.forms[0]
        fv[prefix+'name'] = name
        res = fv.submit('preview')
        assert not 'Error' in res, res

        # check preview has no resources
        res1 = self.main_div(res).replace('</strong>', '')
        assert '<td><a href="">' not in res1, res1

        # submit
        fv = res.forms[0]
        res = fv.submit('commit')

        # check package page
        assert not 'Error' in res, res
        res = res.follow()
        res1 = self.main_div(res).replace('</strong>', '')
        assert '<td><a href="">' not in res1, res1

        # check object created
        pkg = model.Package.by_name(name)
        assert pkg
        assert pkg.name == name
        assert pkg.resources == [], pkg.resources


    def test_new(self):
        assert not model.Package.by_name(u'annakarenina')
        offset = url_for(controller='package', action='new', package_form=package_form)
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
        tags = (u'tag1', u'tag2', u'tag3', u'SomeCaps')
        tags_txt = u' '.join(tags)
##        groups = (u'group1', u'group2', u'group3')
##        groups_txt = u' '.join(groups)
        extras = {'key1':'value1', 'key2':'value2', 'key3':'value3'}
        log_message = 'This is a comment'
        assert not model.Package.by_name(name)
        offset = url_for(controller='package', action='new', package_form=package_form)
        res = self.app.get(offset)
        assert 'Packages - New' in res
        fv = res.forms[0]
        prefix = 'Package--'
        fv[prefix+'name'] = name
        fv[prefix+'title'] = title
        fv[prefix+'version'] = version
        fv[prefix+'url'] = url
        fv[prefix+'resources-0-url'] = download_url
        fv[prefix+'notes'] = notes
        fv[prefix+'license_id'] = license_id
        fv[prefix+'tags'] = tags_txt
##        fv[prefix+'groups'] = groups_txt
        for i, extra in enumerate(extras.items()):
            fv[prefix+'extras-newfield%s-key' % i] = extra[0]
            fv[prefix+'extras-newfield%s-value' % i] = extra[1]
        fv['log_message'] = log_message
        res = fv.submit('preview')
        assert not 'Error' in res, res

        # Check preview is correct
        res1 = str(res).replace('</strong>', '')
        preview =  res1[res1.find('<div id="preview"'):res1.find('<div id="footer">')]
        assert 'Preview' in res
        assert 'Title: %s' % str(title) in preview, preview
        assert 'Version: %s' % str(version) in preview, preview
        assert 'URL: <a href="%s">' % str(url) in preview, preview
        res_html = '<tr> <td><a href="%s">%s</a></td><td>%s</td><td>%s</td>' % (str(download_url), str(download_url), '', '') 
        assert res_html in preview, preview + res_html
        assert '<p>%s' % str(notes) in preview, preview
        assert 'License: %s' % str(license) in preview, preview
        for tag in tags:
            assert '%s</a>' % tag.lower() in preview
        current_extras = extras.items()
        for key, value in current_extras:
            extras_html = '%(key)s: %(value)s' % {'key':key.capitalize(), 'value':value}
            assert extras_html in preview, str(preview) + extras_html
        assert '<li><strong>:</strong> </li>' not in preview, preview

        # Check form is correctly filled
        res1 = self.main_div(res)
        assert 'name="Package--title" size="40" type="text" value="%s"' % title in res1, res1
        assert 'name="Package--version" size="40" type="text" value="%s"' % version in res1, res1
        assert 'name="Package--url" size="40" type="text" value="%s"' % url in res1, res1
        assert 'id="Package--resources-0-url" type="text" value="%s"' % download_url in res1, res1
        assert '<textarea cols="60" id="Package--notes" name="Package--notes" rows="15">%s</textarea>' % notes in res1, res1
        license_html = '<option value="%s" selected>%s' % (license_id, license)
        assert license_html in res1, str(res1) + license_html
        assert 'name="Package--tags" size="60" type="text" value="%s"' % tags_txt.lower() in res1, res1
##        assert 'name="Package--groups" size="60" type="text" value="%s"' % groups_txt in res1, res1
        for key, value in current_extras:
            for html in existing_extra_html:
                extras_html = html % {'package_id':'', 'key':key, 'capitalized_key':key.capitalize(), 'value':value}
                assert extras_html in res1, str(res1) + extras_html
        assert log_message in res1

        # Submit
        res = fv.submit('commit')

        # Check package page
        assert not 'Error' in res, res
        res = res.follow()
        main_res = self.main_div(res).replace('</strong>', '')
        sidebar = self.sidebar(res)
        res1 = (main_res + sidebar).decode('ascii', 'ignore')
        assert 'Packages - %s' % str(name) in res, res
        assert str(name) in res1, res1
        assert str(title) in res1, res1
        assert str(version) in res1, res1
        assert '<a href="%s">' % str(url).lower() in res1.lower(), res1
        assert '<td><a href="%s">' % str(download_url) in res1, res1
        assert '<p>%s' % str(notes) in res1, res1
        assert 'License: %s' % str(license) in res1, res1
        for tag in tags:
            assert '%s</a>' % tag.lower() in res
        for key, value in current_extras:
            extras_html = '%(key)s: %(value)s' % {'key':key.capitalize(), 'value':value}
            assert extras_html in res1, str(res) + extras_html

        # Check package object
        pkg = model.Package.by_name(name)
        assert pkg.name == name
        assert pkg.title == title
        assert pkg.version == version
        assert pkg.url == url
        assert pkg.resources[0].url == download_url
        assert pkg.notes == notes
        assert pkg.license_id == license_id
        saved_tagnames = [str(tag.name) for tag in pkg.tags]
        assert saved_tagnames == [tag.lower() for tag in list(tags)]
        saved_groupnames = [str(group.name) for group in pkg.groups]
        assert len(pkg.extras) == len(current_extras)
        for key, value in current_extras:
            assert pkg.extras[key] == value

        # for some reason environ['REMOTE_ADDR'] is undefined
        rev = model.Revision.youngest()
        assert rev.author == 'Unknown IP Address'
        assert rev.message == log_message
        # TODO: reinstate once fixed in code
        exp_log_message = u'Creating package %s' % name
        # assert rev.message == exp_log_message

    def test_new_existing_name(self):
        # test creating a package with an existing name results in error'
        # create initial package
        assert not model.Package.by_name(self.pkgname)
        offset = url_for(controller='package', action='new', package_form=package_form)
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
        offset = url_for(controller='package', action='new', package_form=package_form)
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
        assert 'Search packages' in res
        form = res.forms[0]
        form['q'] =  str(self.non_active_name)
        results_page = form.submit()
        assert 'Search packages' in results_page, results_page
        print results_page
        assert '<strong>0</strong> packages found' in results_page, (self.non_active_name, results_page)


class TestRevisions(TestController):
    @classmethod
    def setup_class(self):
        model.Session.remove()
        self.name = u'revisiontest1'

        # create pkg
        self.notes = [u'Written by Puccini', u'Written by Rossini', u'Not written at all', u'Written again', u'Written off']
        rev = model.repo.new_revision()
        self.pkg1 = model.Package(name=self.name)
        self.pkg1.notes = self.notes[0]
        model.setup_default_user_roles(self.pkg1)
        model.repo.commit_and_remove()

        # edit pkg
        for i in range(5)[1:]:
            rev = model.repo.new_revision()
            pkg1 = model.Package.by_name(self.name)
            pkg1.notes = self.notes[i]
            model.repo.commit_and_remove()

        self.pkg1 = model.Package.by_name(self.name)        

    @classmethod
    def _teardown_class(self):
        rev = model.repo.new_revision()
        pkg1 = model.Package.by_name(self.name)
        pkg1.purge()
        model.repo.commit_and_remove()
    
    def test_0_read_history(self):
        offset = url_for(controller='package', action='history', id=self.pkg1.name)
        res = self.app.get(offset)
        main_res = self.main_div(res)
        assert self.pkg1.name in main_res, main_res
        assert 'radio' in main_res, main_res
        latest_rev = self.pkg1.all_revisions[0]
        oldest_rev = self.pkg1.all_revisions[-1]
        first_radio_checked_html = '<input checked="checked" id="selected1_%s"' % latest_rev.revision_id
        assert first_radio_checked_html in main_res, '%s %s' % (first_radio_checked_html, main_res)
        last_radio_checked_html = '<input checked="checked" id="selected2_%s"' % oldest_rev.revision_id
        assert last_radio_checked_html in main_res, '%s %s' % (last_radio_checked_html, main_res)

    def test_1_do_diff(self):
        offset = url_for(controller='package', action='history', id=self.pkg1.name)
        res = self.app.get(offset)
        form = res.forms[0]
        res = form.submit()
        res = res.follow()
        main_res = self.main_div(res)
        assert 'error' not in main_res.lower(), main_res
        assert 'Revision Differences' in main_res, main_res
        assert self.pkg1.name in main_res, main_res
        assert '<tr><td>notes</td><td><pre>- Written by Puccini\n+ Written off</pre></td></tr>' in main_res, main_res
