import cgi

from paste.fixture import AppError

from ckan.tests import *
import ckan.model as model
from ckan.lib.create_test_data import CreateTestData
import ckan.lib.helpers as h
from genshi.core import escape as genshi_escape

existing_extra_html = ('<label class="field_opt" for="Package-%(package_id)s-extras-%(key)s">%(capitalized_key)s</label>', '<input id="Package-%(package_id)s-extras-%(key)s" name="Package-%(package_id)s-extras-%(key)s" size="20" type="text" value="%(value)s">')

package_form=''

class TestPackageBase(TestController):
    key1 = u'key1 Less-than: < Umlaut: \xfc'
    value1 = u'value1 Less-than: < Umlaut: \xfc'
    # Note: Can't put a quotation mark in key1 or value1 because
    # paste.fixture doesn't unescape the value in an input field
    # on form submission. (But it works in real life.)
    
    def _assert_form_errors(self, res):
        self.check_tag(res, '<form', 'class="has-errors"')
        assert 'class="field_error"' in res, res

class TestPackageForm(TestPackageBase):
    '''Inherit this in tests for these form testing methods'''
    def _check_package_read(self, res, **params):
        assert not 'Error' in res, res
        assert u'Packages - %s' % params['name'] in res, res
        main_res = self.main_div(res)
        main_div = main_res
        main_div_str = main_div.encode('utf8')
        assert params['name'] in main_div, main_div_str
        assert params['title'] in main_div, main_div_str
        assert params['version'] in main_div, main_div_str
        assert '<a href="%s">' % params['url'] in main_div, main_div_str
        prefix = 'Package-%s-' % params.get('id', '')
        for res_index, values in self._get_resource_values(params['resources'], by_resource=True):
            self.check_named_element(main_div, 'tr', *values)
        assert params['notes'] in main_div, main_div_str
        license = model.Package.get_license_register()[params['license_id']]
        assert license.title in main_div, (license.title, main_div_str)
        tag_names = [tag.lower() for tag in params['tags']]
        self.check_named_element(main_div, 'ul', *tag_names)
        if params.has_key('state'):
            assert 'State: %s' % params['state'] in main_div.replace('</strong>', ''), main_div_str
        if isinstance(params['extras'], dict):
            extras = params['extras'].items()
        elif isinstance(params['extras'], (list, tuple)):
            extras = params['extras']
        else:
            raise NotImplementedError
        for key, value in extras:
            key_in_html_body = self.escape_for_html_body(key)
            value_in_html_body = self.escape_for_html_body(value)
            self.check_named_element(main_div, 'tr', key_in_html_body, value_in_html_body)
        if params.has_key('deleted_extras'):
            if isinstance(params['deleted_extras'], dict):
                deleted_extras = params['deleted_extras'].items()
            elif isinstance(params['deleted_extras'], (list, tuple)):
                deleted_extras = params['deleted_extras']
            else:
                raise NotImplementedError
            for key, value in params['deleted_extras']:
                self.check_named_element(main_div, 'tr', '!' + key)
                self.check_named_element(main_div, 'tr', '!' + value)

    def _check_preview(self, res, **params):
        preview =  str(res)[str(res).find('<div id="preview"'):str(res).find('<div id="footer">')]
        assert 'Preview' in preview, preview
        assert str(params['name']) in preview, preview
        assert str(params['title']) in preview, preview
        assert str(params['version']) in preview, preview
        assert '<a href="%s">' % str(params['url']) in preview, preview
        for res_index, resource in enumerate(params['resources']):
            if isinstance(resource, (str, unicode)):
                resource = [resource]
            self.check_named_element(preview, 'tr', resource[0], resource[1], resource[2], resource[3])
        preview_ascii = repr(preview)
        assert str(params['notes']) in preview_ascii, preview_ascii
        license = model.Package.get_license_register()[params['license_id']]
        assert license.title in preview_ascii, (license.title, preview_ascii)
        tag_names = [str(tag.lower()) for tag in params['tags']]
        self.check_named_element(preview, 'ul', *tag_names)
        if params.has_key('state'):
            assert str(params['state']) in preview, preview
        else:
            assert 'state' not in preview
        for key, value in params['extras']:
            key_html = self.escape_for_html_body(key)
            value_html = self.escape_for_html_body(value)
            self.check_named_element(preview, 'tr', key_html, value_html)
        if params.has_key('deleted_extras'):
            for key, value in params['deleted_extras']:
                key_html = self.escape_for_html_body(key)
                value_html = self.escape_for_html_body(value)
                self.check_named_element(preview, 'tr', '!' + key_html)
                self.check_named_element(preview, 'tr', '!' + value_html)

    def _get_resource_values(self, resources, by_resource=False):
        assert isinstance(resources, (list, tuple))
        for res_index, resource in enumerate(resources):
            if by_resource:
                values = []
            for i, res_field in enumerate(model.PackageResource.get_columns()):
                if isinstance(resource, (str, unicode)):
                    expected_value = resource if res_field == 'url' else ''
                elif hasattr(resource, res_field):
                    expected_value = getattr(resource, res_field)
                elif isinstance(resource, (list, tuple)):
                    expected_value = resource[i]
                elif isinstance(resource, dict):
                    expected_value = resource.get(res_field, u'')
                else:
                    raise NotImplemented
                if not by_resource:
                    yield (res_index, res_field, expected_value)
                else:
                    values.append(expected_value)
            if by_resource:
                yield(res_index, values)

    def escape_for_html_body(self, unescaped_str):
        # just deal with chars in tests
        return unescaped_str.replace('<', '&lt;')

    def check_form_filled_correctly(self, res, **params):
        if params.has_key('pkg'):
            for key, value in params['pkg'].as_dict().items():
                if key == 'license':
                    key = 'license_id'
                params[key] = value
        prefix = 'Package-%s-' % params['id']
        main_res = self.main_div(res)
        self.check_tag(main_res, prefix+'name', params['name'])
        self.check_tag(main_res, prefix+'title', params['title'])
        self.check_tag(main_res, prefix+'version', params['version'])
        self.check_tag(main_res, prefix+'url', params['url'])
        for res_index, res_field, expected_value in self._get_resource_values(params['resources']):
            self.check_tag(main_res, '%sresources-%i-%s' % (prefix, res_index, res_field), expected_value)
        self.check_tag_and_data(main_res, prefix+'notes', params['notes'])
        self.check_tag_and_data(main_res, 'selected', params['license_id'])
        if isinstance(params['tags'], (str, unicode)):
            tags = params['tags'].split()
        else:
            tags = params['tags']
        for tag in tags:
            self.check_tag(main_res, prefix+'tags', tag)
        if params.has_key('state'):
            self.check_tag_and_data(main_res, 'selected', str(params['state']))
        if isinstance(params['extras'], dict):
            extras = params['extras'].items()
        else:
            extras = params['extras']
        for key, value in extras:
            key_in_html_body = self.escape_for_html_body(key)
            value_in_html_body = self.escape_for_html_body(value)
            key_escaped = genshi_escape(key)
            value_escaped = genshi_escape(value)
            self.check_tag_and_data(main_res, 'Package-%s-extras-%s' % (params['id'], key_escaped), key_in_html_body.capitalize())
            self.check_tag(main_res, 'Package-%s-extras-%s' % (params['id'], key_escaped), value_escaped)
        assert params['log_message'] in main_res, main_res
    

class TestReadOnly(TestPackageForm):

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
        assert 'Browse' in res, res
        res = res.click('Browse packages')
        assert 'Packages - List' in res
    
    def test_minornavigation_2(self):
        offset = url_for(controller='package')
        res = self.app.get(offset)
        res = res.click('Register a new package')
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
        assert self.anna.resources[0].hash in res
        assert 'Some test notes' in res
        assert '<strong>Some bolded text.</strong>' in res
        self.check_tag_and_data(res, 'left arrow', '&lt;')
        self.check_tag_and_data(res, 'umlaut', u'\xfc')
        assert 'License:' in res
        #assert 'OKD Compliant::' in res
        assert 'russian' in res
        assert 'david' in res
        assert 'roger' in res
        assert 'State:' not in res
        assert 'genre' in res, res
        assert 'romantic novel' in res, res
        assert 'original media' in res, res
        assert 'book' in res, res

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
        main_div = self.main_div(res)
        assert title in main_div, main_div.encode('utf8')

    def test_search(self):
        offset = url_for(controller='package', action='search')
        res = self.app.get(offset)
        assert 'Search packages' in res
        self._check_search_results(res, 'annakarenina', ['<strong>1</strong>', 'A Novel By Tolstoy'] )
        self._check_search_results(res, 'warandpeace', ['<strong>0</strong>'], only_downloadable=True )
        self._check_search_results(res, 'warandpeace', ['<strong>0</strong>'], only_open=True )
        self._check_search_results(res, 'annakarenina', ['<strong>1</strong>'], only_open=True, only_downloadable=True )
        # check for something that also finds tags ...
        self._check_search_results(res, 'russian', ['<strong>2</strong>'])

    def _check_search_results(self, page, terms, requireds, only_open=False, only_downloadable=False):
        form = page.forms[0]
        form['q'] = str(terms)
        form['open_only'] = only_open
        form['downloadable_only'] = only_downloadable
        results_page = form.submit()
        assert 'Search packages' in results_page, results_page
        results_page = self.main_div(results_page)
        for required in requireds:
            assert required in results_page, "%s : %s" % (results_page, required)
    
    def test_history(self):
        name = 'annakarenina'
        offset = url_for(controller='package', action='history', id=name)
        res = self.app.get(offset)
        assert 'History' in res
        assert 'Revisions' in res
        assert name in res

class TestEdit(TestPackageForm):
    def setup_method(self, method):
        self.setUp()

    def setUp(self):
        model.Session.remove()
        rev = model.repo.new_revision()
        self.editpkg_name = u'editpkgtest'
        editpkg = model.Package(name=self.editpkg_name)
        editpkg.url = u'editpkgurl.com'
        editpkg.notes = u'Some notes'
        editpkg.add_tag_by_name(u'mytesttag')
        editpkg.add_resource(u'url escape: & umlaut: \xfc quote: "',
                             description=u'description escape: & umlaut: \xfc quote "')
        model.Session.add(editpkg)
        u = model.User(name=u'testadmin')
        model.Session.add(u)
        model.repo.commit_and_remove()

        editpkg = model.Package.by_name(self.editpkg_name)
        admin = model.User.by_name(u'testadmin')
        model.setup_default_user_roles(editpkg, [admin])
        model.repo.commit_and_remove()

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
        model.repo.rebuild_db()
        model.Session.remove()

    def test_edit(self):
        # the absolute basics
        assert 'Packages - Edit' in self.res, self.res
        assert self.editpkg.notes in self.res

        new_name = u'new-name'
        new_title = u'A Short Description of this Package'
        newurl = u'http://www.editpkgnewurl.com'
        new_download_url = newurl + u'/download/'
        newlicense_id = u'cc-by'
        newversion = u'0.9b'
        fv = self.res.forms[0]
        prefix = 'Package-%s-' % self.pkgid
        fv[prefix + 'name'] = new_name
        fv[prefix + 'title'] =  new_title
        fv[prefix + 'url'] =  newurl
        fv[prefix + 'resources-0-url'] =  new_download_url
        fv[prefix + 'license_id'] =  newlicense_id
        fv[prefix + 'version'] = newversion
        res = fv.submit('commit')
        # get redirected ...
        res = res.follow()
        model.Session.remove()
        offset = url_for(controller='package', action='read', id=new_name)
        res = self.app.get(offset)
        assert 'Packages - %s' % new_name in res, res
        pkg = model.Package.by_name(new_name)
        assert pkg.title == new_title 
        assert pkg.url == newurl
        assert pkg.resources[0].url == new_download_url
        assert pkg.version == newversion
        assert newlicense_id == pkg.license.id

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
        rev = model.Revision.youngest(model.Session)
        assert rev.author == 'Unknown IP Address'
        assert rev.message == exp_log_message

    def test_edit_preview(self):
        newurl = 'www.editpkgnewurl.com'
        newnotes = '''
### A title

Hello world.

Arrow <

u with umlaut \xc3\xbc

'''
        fv = self.res.forms[0]
        prefix = 'Package-%s-' % self.pkgid
        fv[prefix + 'url'] =  newurl
        fv[prefix + 'notes'] =  newnotes
        res = fv.submit('preview')
        print str(res)
        assert 'Packages - Edit' in res
        assert 'Preview' in res
        assert 'Hello world' in res
        self.check_tag_and_data(res, 'umlaut', u'\xfc')
        self.check_tag_and_data(res, 'Arrow', '&lt;')

    def test_edit_bad_name(self):
        fv = self.res.forms[0]
        prefix = 'Package-%s-' % self.pkgid
        fv[prefix + 'name'] = u'a' # invalid name
        res = fv.submit('preview')
        assert 'Error' in res, res
        assert 'Name must be at least 2 characters long' in res, res
        # Ensure there is an error at the top of the form and by the field
        self._assert_form_errors(res)

        res = fv.submit('commit')
        assert 'Error' in res, res
        assert 'Name must be at least 2 characters long' in res, res
        # Ensure there is an error at the top of the form and by the field
        self._assert_form_errors(res)

    def test_missing_fields(self):
        # User edits and a field is left out in the commit parameters.
        # (Spammers can cause this)
        fv = self.res.forms[0]
        del fv.fields['log_message']
        res = fv.submit('commit', status=400)

        fv = self.res.forms[0]
        prefix = 'Package-%s-' % self.pkgid
        del fv.fields[prefix + 'license_id']
        res = fv.submit('commit', status=400)     

    def test_edit_all_fields(self):
        # Create new item
        rev = model.repo.new_revision()
        pkg_name = u'new_editpkgtest'
        pkg = model.Package(name=pkg_name)
        pkg.title = u'This is a Test Title'
        pkg.url = u'editpkgurl.com'
        pr1 = model.PackageResource(url=u'editpkgurl1',
              format=u'plain text', description=u'Full text',
              hash=u'123abc',)
        pr2 = model.PackageResource(url=u'editpkgurl2',
              format=u'plain text2', description=u'Full text2',
              hash=u'456abc',)
        pkg.resources.append(pr1)
        pkg.resources.append(pr2)
        pkg.notes= u'this is editpkg'
        pkg.version = u'2.2'
        t1 = model.Tag(name=u'one')
        t2 = model.Tag(name=u'two')
        pkg.tags = [t1, t2]
        pkg.state = model.State.DELETED
        pkg.license_id = u'other-open'
        extras = {'key1':'value1', 'key2':'value2', 'key3':'value3'}
        for key, value in extras.items():
            pkg.extras[unicode(key)] = unicode(value)
        for obj in [pkg, t1, t2, pr1, pr2]:
            model.Session.add(obj)
        model.repo.commit_and_remove()
        pkg = model.Package.by_name(pkg_name)
        model.setup_default_user_roles(pkg, [self.admin])
        model.repo.commit_and_remove()

        # Edit it
        offset = url_for(controller='package', action='edit', id=pkg.name, package_form=package_form)
        res = self.app.get(offset, status=200, extra_environ={'REMOTE_USER':'testadmin'})
        assert 'Packages - Edit' in res, res
        
        # Check form is correctly filled
        self.check_form_filled_correctly(res, pkg=pkg, log_message='')
                                         
        # Amend form
        name = u'test_name'
        title = u'Test Title'
        version = u'1.1'
        url = u'http://something.com/somewhere.zip'
        resources = ((u'http://something.com/somewhere-else.xml', u'xml', u'Best', u'hash1'),
                     (u'http://something.com/somewhere-else2.xml', u'xml2', u'Best2', u'hash2'),
                     )
        assert len(resources[0]) == len(model.PackageResource.get_columns())
        notes = u'Very important'
        license_id = u'gpl-3.0'
        state = model.State.ACTIVE
        tags = (u'tag1', u'tag2', u'tag3')
        tags_txt = u' '.join(tags)
        extra_changed = 'key1', self.value1 + ' CHANGED'
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
            for field_index, res_field in enumerate(model.PackageResource.get_columns()):
                fv[prefix+'resources-%s-%s' % (res_index, res_field)] = resource[field_index]
        fv[prefix+'notes'] = notes
        fv[prefix+'license_id'] = license_id
        fv[prefix+'tags'] = tags_txt
        fv[prefix+'state'] = state
        fv[prefix+'extras-%s' % extra_changed[0]] = extra_changed[1].encode('utf8')
        fv[prefix+'extras-newfield0-key'] = extra_new[0].encode('utf8')
        fv[prefix+'extras-newfield0-value'] = extra_new[1].encode('utf8')
        fv[prefix+'extras-key3-checkbox'] = True
        fv['log_message'] = log_message
        res = fv.submit('preview', extra_environ={'REMOTE_USER':'testadmin'})
        assert not 'Error' in res, res

        # Check preview is correct
        current_extras = (('key2', extras['key2']),
                          extra_changed,
                          extra_new)
        deleted_extras = [('key3', extras['key3'])]
        self._check_preview(res, name=name, title=title, version=version,
                            url=url,
                            download_url='',
                            resources=resources, notes=notes, license_id=license_id,
                            tags=tags, extras=current_extras,
                            deleted_extras=deleted_extras,
                            state=state)
                            
        # Check form is correctly filled
        self.check_form_filled_correctly(res, id=pkg.id, name=name,
                                         title=title, version=version,
                                         url=url, resources=resources,
                                         notes=notes, license_id=license_id,
                                         tags=tags, extras=current_extras,
                                         deleted_extras=deleted_extras,
                                         log_message=log_message,
                                         state=state)

        # Submit
        fv = res.forms[0]
        res = fv.submit('commit', extra_environ={'REMOTE_USER':'testadmin'})

        # Check package page
        assert not 'Error' in res, res
        res = res.follow(extra_environ={'REMOTE_USER':'testadmin'})
        self._check_package_read(res, name=name, title=title,
                                 version=version, url=url,
                                 resources=resources, notes=notes,
                                 license_id=license_id, 
                                 tags=tags,
                                 extras=current_extras,
                                 deleted_extras=deleted_extras,
                                 state=state,
                                 )

        # Check package object
        pkg = model.Package.by_name(name)
        assert pkg.name == name
        assert pkg.title == title
        assert pkg.version == version
        assert pkg.url == url
        for res_index, resource in enumerate(resources):
            for field_index, res_field in enumerate(model.PackageResource.get_columns()):
                assert getattr(pkg.resources[res_index], res_field) == resource[field_index]
        assert pkg.notes == notes
        assert pkg.license.id == license_id
        saved_tagnames = [str(tag.name) for tag in pkg.tags]
        saved_tagnames.sort()
        expected_tagnames = list(tags)
        expected_tagnames.sort()
        assert saved_tagnames == expected_tagnames
        assert pkg.state == state
        assert len(pkg.extras) == len(current_extras)
        for key, value in current_extras:
            assert pkg.extras[key] == value

        # for some reason environ['REMOTE_ADDR'] is undefined
        rev = model.Revision.youngest(model.Session)
        assert rev.author == 'testadmin', rev.author
        assert rev.message == log_message
        # TODO: reinstate once fixed in code
        exp_log_message = u'Creating package %s' % name
        #assert rev.message == exp_log_message

    def test_edit_bad_log_message(self):
        fv = self.res.forms[0]
        prefix = 'Package-%s-' % self.pkgid
        fv['log_message'] = u'Free enlargements: http://drugs.com/' # spam
        res = fv.submit('preview')
        assert 'Error' in res, res
        assert 'No links are allowed' in res, res
        self.check_tag(res, '<form', 'class="has-errors"')
        assert 'No links are allowed' in res, res

        res = fv.submit('commit')
        assert 'Error' in res, res
        self.check_tag(res, '<form', 'class="has-errors"')
        assert 'No links are allowed' in res, res


class TestMarkdownHtmlWhitelist(TestPackageForm):

    pkg_name = u'markdownhtmlwhitelisttest'
    pkg_notes = u'''
<table width="100%" border="1">
<tr>
<td rowspan="2"><b>Description</b></td>
<td rowspan="2"><b>Documentation</b></td>

<td colspan="2"><b><center>Data -- Pkzipped</center></b> </td>
</tr>
<tr>
<td><b>SAS .tpt</b></td>
<td><b>ASCII CSV</b> </td>
</tr>
<tr>
<td><b>Overview</b></td>
<td><A HREF="http://www.nber.org/patents/subcategories.txt">subcategory.txt</A></td>
<td colspan="2"><center>--</center></td>
</tr>
<script><!--
alert('Hello world!');
//-->
</script>

'''

    def setup_method(self, method):
        self.setUp()

    def setUp(self):
        model.Session.remove()
        rev = model.repo.new_revision()
        self.pkg = model.Package(name=self.pkg_name, notes=self.pkg_notes)
        model.Session.add(self.pkg)
        u = model.User(name=u'testadmin')
        model.Session.add(u)
        model.repo.commit_and_remove()

        self.pkg = model.Package.by_name(self.pkg_name)
        admin = model.User.by_name(u'testadmin')
        model.setup_default_user_roles(self.pkg, [admin])
        model.repo.commit_and_remove()
        self.pkg_id = self.pkg.id
        offset = url_for(controller='package', action='read', id=self.pkg_name)
        self.res = self.app.get(offset)
        model.repo.commit_and_remove()

        self.pkg = model.Package.by_name(self.pkg_name)
        self.admin = model.User.by_name(u'testadmin')

    def teardown_method(self, method):
        self.tearDown()

    def tearDown(self):
        model.repo.rebuild_db()
        model.Session.remove()

    def test_markdown_html_whitelist(self):
        self.body = str(self.res)
        self.assert_fragment('<table width="100%" border="1">')
        self.assert_fragment('<td rowspan="2"><b>Description</b></td>')
        self.assert_fragment('<a href="http://www.nber.org/patents/subcategories.txt">subcategory.txt</a>')
        self.assert_fragment('<td colspan="2"><center>--</center></td>')
        self.fail_if_fragment('<script>')

    def assert_fragment(self, fragment):
        assert fragment in self.body, (fragment, self.body)

    def fail_if_fragment(self, fragment):
        assert fragment not in self.body, (fragment, self.body)


class TestNew(TestPackageForm):
    pkgname = u'testpkg'
    pkgtitle = u'mytesttitle'

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()
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
        assert not pkg.resources, pkg.resources


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

    def test_new_bad_name(self):
        offset = url_for(controller='package', action='new', package_form=package_form)
        res = self.app.get(offset)
        assert 'Packages - New' in res
        fv = res.forms[0]
        prefix = 'Package--'
        fv[prefix + 'name'] = u'a' # invalid name
        res = fv.submit('preview')
        assert 'Error' in res, res
        assert 'Name must be at least 2 characters long' in res, res
        self._assert_form_errors(res)

        res = fv.submit('commit')
        assert 'Error' in res, res
        assert 'Name must be at least 2 characters long' in res, res
        self._assert_form_errors(res)

    def test_new_all_fields(self):
        name = u'test_name2'
        title = u'Test Title'
        version = u'1.1'
        url = u'http://something.com/somewhere.zip'
        download_url = u'http://something.com/somewhere-else.zip'
        notes = u'Very important'
        license_id = u'gpl-3.0'
        tags = (u'tag1', u'tag2', u'tag3', u'SomeCaps')
        tags_txt = u' '.join(tags)
        extras = {self.key1:self.value1, 'key2':'value2', 'key3':'value3'}
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
        fv[prefix+'resources-0-description'] = u'description escape: & umlaut: \xfc quote "'.encode('utf8')
        fv[prefix+'notes'] = notes
        fv[prefix+'license_id'] = license_id
        fv[prefix+'tags'] = tags_txt
        for i, extra in enumerate(extras.items()):
            fv[prefix+'extras-newfield%s-key' % i] = extra[0].encode('utf8')
            fv[prefix+'extras-newfield%s-value' % i] = extra[1].encode('utf8')
        fv['log_message'] = log_message
        res = fv.submit('preview')
        assert not 'Error' in res, res

        # Check preview is correct
        resources = [[download_url, u'', u'description escape: & umlaut: \xfc quote "', u'']]
        resources_escaped = [[download_url, u'', u'description escape: &amp; umlaut: \xfc quote "', u'']]
        self._check_preview(res, name=name, title=title, version=version,
                            url=url,
                            resources=resources_escaped, notes=notes,
                            license_id=license_id,
                            tags=tags, extras=extras.items(),
                            )

        # Check form is correctly filled
        self.check_form_filled_correctly(res, id='', name=name,
                                         title=title, version=version,
                                         url=url, resources=[download_url],
                                         notes=notes, license_id=license_id,
                                         tags=[tag.lower() for tag in tags],
                                         extras=extras,
#                                         deleted_extras=deleted_extras,
                                         log_message=log_message,
#                                         state=state
                                         )
        # Submit
        fv = res.forms[0]
        res = fv.submit('commit')

        # Check package page
        assert not 'Error' in res, res
        res = res.follow()
        self._check_package_read(res, name=name, title=title,
                                 version=version, url=url,
                                 resources=[download_url], notes=notes,
                                 license_id=license_id, 
                                 tags=tags,
                                 extras=extras,
#                                 state=state,
                                 )

        # Check package object
        pkg = model.Package.by_name(name)
        assert pkg.name == name
        assert pkg.title == title
        assert pkg.version == version
        assert pkg.url == url
        assert pkg.resources[0].url == download_url
        assert pkg.notes == notes
        assert pkg.license.id == license_id
        saved_tagnames = [str(tag.name) for tag in pkg.tags]
        saved_tagnames.sort()
        expected_tagnames = [tag.lower() for tag in tags]
        expected_tagnames.sort()
        assert saved_tagnames == expected_tagnames, '%r != %r' % (saved_tagnames, expected_tagnames)
        saved_groupnames = [str(group.name) for group in pkg.groups]
        assert len(pkg.extras) == len(extras)
        for key, value in extras.items():
            assert pkg.extras[key] == value

        # for some reason environ['REMOTE_ADDR'] is undefined
        rev = model.Revision.youngest(model.Session)
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
        self._assert_form_errors(res)
        
    def test_missing_fields(self):
        # A field is left out in the commit parameters.
        # (Spammers can cause this)
        offset = url_for(controller='package', action='new', package_form=package_form)
        res = self.app.get(offset)
        assert 'Packages - New' in res
        prefix = 'Package--'
        fv = res.forms[0]
        fv[prefix + 'name'] = 'anything'
        del fv.fields['log_message']
        res = fv.submit('commit', status=400)

        offset = url_for(controller='package', action='new', package_form=package_form)
        res = self.app.get(offset)
        assert 'Packages - New' in res
        fv = res.forms[0]
        fv[prefix + 'name'] = 'anything'
        prefix = 'Package--'
        del fv.fields[prefix + 'notes']
        # NOTE Missing dropdowns fields don't cause KeyError in
        # _serialized_value so don't register as an error here like
        # text field tested here.
        res = fv.submit('commit', status=400)     

    def test_multi_resource_bug(self):
        # ticket:276
        offset = url_for(controller='package', action='new', package_form=package_form)
        res = self.app.get(offset)
        assert 'Packages - New' in res
        fv = res.forms[0]
        prefix = 'Package--'
        fv[prefix + 'name'] = 'name276'
        resformat = u'xls'    
        fv[prefix + 'resources-0-format'] = resformat
        res = fv.submit('preview')

        res = self.main_div(res)
        assert resformat in res, res
        assert res.count(str(resformat)) == 1, res.count(str(resformat))

class TestNewPreview(TestPackageBase):
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

    def test_preview(self):
        assert model.Session.query(model.Package).count() == 0, model.Session.query(model.Package).all()
        
        offset = url_for(controller='package', action='new', package_form=package_form)
        res = self.app.get(offset)
        assert 'Packages - New' in res
        fv = res.forms[0]
        prefix = 'Package--'
        fv[prefix + 'name'] = self.pkgname
        fv[prefix + 'title'] = self.pkgtitle
        res = fv.submit('preview')
        assert not 'Error' in res, res

        # Check preview displays correctly
        assert str(self.pkgname) in res, res
        assert str(self.pkgtitle) in res, res

        # Check no object is yet created
        assert model.Session.query(model.Package).count() == 0, model.Session.query(model.Package).all()
        

class TestNonActivePackages(TestPackageBase):

    @classmethod
    def setup_class(self):
        CreateTestData.create()
        self.non_active_name = u'test_nonactive'
        pkg = model.Package(name=self.non_active_name)
        model.repo.new_revision()
        model.Session.add(pkg)
        model.repo.commit_and_remove()

        pkg = model.Session.query(model.Package).filter_by(name=self.non_active_name).one()
        admin = model.User.by_name(u'joeadmin')
        model.setup_default_user_roles(pkg, [admin])
        model.repo.commit_and_remove()
        
        pkg = model.Session.query(model.Package).filter_by(name=self.non_active_name).one()
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


class TestRevisions(TestPackageBase):
    @classmethod
    def setup_class(self):
        model.Session.remove()
        self.name = u'revisiontest1'

        # create pkg
        self.notes = [u'Written by Puccini', u'Written by Rossini', u'Not written at all', u'Written again', u'Written off']
        rev = model.repo.new_revision()
        self.pkg1 = model.Package(name=self.name)
        self.pkg1.notes = self.notes[0]
        model.Session.add(self.pkg1)
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
    def teardown_class(self):
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

    def test_2_atom_feed(self):
        offset = url_for(controller='package', action='history', id=self.pkg1.name)
        offset = "%s?format=atom" % offset
        res = self.app.get(offset)
        assert '<feed' in res, res
        assert 'xmlns="http://www.w3.org/2005/Atom"' in res, res
        assert '</feed>' in res, res
   
