from ckan.tests import *
import ckan.model as model

class TestGroup(TestController):

    @classmethod
    def setup_class(self):
        model.Session.remove()
        CreateTestData.create()

    @classmethod
    def teardown_class(self):
        CreateTestData.delete()

    def test_mainmenu(self):
        offset = url_for(controller='home', action='index')
        res = self.app.get(offset)
        assert 'Groups' in res, res
        assert 'Groups</a></li>' in res, res
        res = res.click('Groups')
        assert '<h2>Groups</h2>' in res, res

    def test_index(self):
        offset = url_for(controller='group')
        res = self.app.get(offset)
        assert '<h2>Groups</h2>' in res, res
        group_count = model.Session.query(model.Group).count()
        assert 'There are %s groups.' % group_count in self.strip_tags(res)
        groupname = 'david'
        group = model.Group.by_name(unicode(groupname))
        group_title = group.title
        group_packages_count = len(group.packages)
        group_description = group.description
        self.check_named_element(res, 'tr', group_title, group_packages_count, group_description)
        res = res.click(group_title)
        assert groupname in res
        
    def test_read(self):
        name = u'david'
        pkgname = u'warandpeace'
        offset = url_for(controller='group', action='read', id=name)
        res = self.app.get(offset)
        main_res = self.main_div(res)
        assert 'Groups - %s' % name in res, res
        assert '[edit]' not in main_res, main_res
        assert 'Administrators:' in main_res, main_res
        assert 'russianfan' in main_res, main_res
        assert name in res, res
        assert 'There are 2 packages in this group' in self.strip_tags(main_res), main_res
        res = res.click(model.Package.by_name(pkgname).title)
        assert 'Packages - %s' % pkgname in res

    def test_read_and_authorized_to_edit(self):
        name = u'david'
        pkgname = u'warandpeace'
        offset = url_for(controller='group', action='read', id=name)
        res = self.app.get(offset, extra_environ={'REMOTE_USER': 'russianfan'})
        assert 'Groups - %s' % name in res, res
        assert '[edit]' in res
        assert name in res

    def test_new(self):
        offset = url_for(controller='group')
        res = self.app.get(offset, extra_environ={'REMOTE_USER': 'russianfan'})
        assert 'Create a new group' in res, res
        

class TestEdit(TestController):
    groupname = u'david'

    @classmethod
    def setup_class(self):
        model.Session.remove()
        CreateTestData.create()
        self.packagename = u'testpkg'
        model.repo.new_revision()
        model.Session.add(model.Package(name=self.packagename))
        model.repo.commit_and_remove()

    @classmethod
    def teardown_class(self):
        model.Session.remove()
        model.repo.rebuild_db()
        model.Session.remove()

    def test_0_not_authz(self):
        offset = url_for(controller='group', action='edit', id=self.groupname)
        # 401 gets caught by repoze.who and turned into redirect
        res = self.app.get(offset, status=[302, 401])
        res = res.follow()
        assert res.request.url.startswith('/user/login')

    def test_1_read_allowed_for_admin(self):
        offset = url_for(controller='group', action='edit', id=self.groupname)
        res = self.app.get(offset, status=200, extra_environ={'REMOTE_USER': 'russianfan'})
        assert 'Edit Group: %s' % self.groupname in res, res
        
    def test_2_edit(self):
        offset = url_for(controller='group', action='edit', id=self.groupname)
        res = self.app.get(offset, status=200, extra_environ={'REMOTE_USER': 'russianfan'})
        print res
        assert 'Edit Group: %s' % self.groupname in res, res

        form = res.forms[0]
        group = model.Group.by_name(self.groupname)
        titlefn = 'Group-%s-title' % group.id
        descfn = 'Group-%s-description' % group.id
        newtitle = 'xxxxxxx'
        newdesc = '''### Lots of stuff here

Ho ho ho
'''

        form[titlefn] = newtitle
        form[descfn] = newdesc
        pkg = model.Package.by_name(self.packagename)
        form['PackageGroup--package_id'] = pkg.id

        
        res = form.submit('commit', status=302, extra_environ={'REMOTE_USER': 'russianfan'})
        # should be read page
        # assert 'Groups - %s' % self.groupname in res, res
        
        model.Session.remove()
        group = model.Group.by_name(self.groupname)
        assert group.title == newtitle, group
        assert group.description == newdesc, group

        # now look at packages
        assert len(group.packages) == 3

    def test_3_edit_form_has_new_package(self):
        # check for package in autocomplete
        offset = url_for(controller='package', action='autocomplete')
        res = self.app.get(offset, status=200, extra_environ={'REMOTE_USER': 'russianfan'})
        assert 'annakarenina' in res, res
        assert not 'newone' in res, res

        pkg = model.Package(name=u'newone')
        model.Session.add(pkg)
        model.repo.new_revision()
        model.repo.commit_and_remove()

        pkg = model.Package.by_name(u'newone')
        user = model.User.by_name(u'russianfan')
        model.setup_default_user_roles(pkg, [user])
        model.repo.new_revision()
        model.repo.commit_and_remove()
        
        res = self.app.get(offset, status=200, extra_environ={'REMOTE_USER': 'russianfan'})
        assert 'annakarenina' in res, res
        assert 'newone' in res

class TestNew(TestController):
    groupname = u'david'

    @classmethod
    def setup_class(self):
        model.Session.remove()
        CreateTestData.create()
        
        self.packagename = u'testpkg'
        model.repo.new_revision()
        model.Session.add(model.Package(name=self.packagename))
        model.repo.commit_and_remove()

    @classmethod
    def teardown_class(self):
        model.Session.remove()
        model.repo.rebuild_db()
        model.Session.remove()

    def test_1_not_authz(self):
        offset = url_for(controller='group', action='new')
        # 401 gets caught by repoze.who and turned into redirect
        res = self.app.get(offset, status=[302, 401])
        res = res.follow()
        assert res.request.url.startswith('/user/login')

    def test_2_new(self):
        prefix = 'Group--'
        group_name = u'testgroup'
        group_title = u'Test Title'
        group_description = u'A Description'

        # Open 'new group' page
        offset = url_for(controller='group', action='new')
        res = self.app.get(offset, status=200, extra_environ={'REMOTE_USER': 'russianfan'})
        assert 'New Group' in res, res
        fv = res.forms[0]
        assert fv[prefix+'name'].value == '', fv.fields
        assert fv[prefix+'title'].value == ''
        assert fv[prefix+'description'].value == ''
        assert fv['PackageGroup--package_id'].value == '', fv['PackageGroup--package_id'].value

        # Edit form
        fv[prefix+'name'] = group_name
        fv[prefix+'title'] = group_title
        fv[prefix+'description'] = group_description
        pkg = model.Package.by_name(self.packagename)
        fv['PackageGroup--package_id'] = pkg.id
        res = fv.submit('commit', status=302, extra_environ={'REMOTE_USER': 'russianfan'})
        res = res.follow()
        assert '%s' % group_title in res, res
        
        model.Session.remove()
        group = model.Group.by_name(group_name)
        assert group.title == group_title, group
        assert group.description == group_description, group
        assert len(group.packages) == 1
        pkg = model.Package.by_name(self.packagename)
        assert group.packages == [pkg]

    def test_3_new_duplicate(self):
        prefix = 'Group--'

        # Create group
        group_name = u'testgrp1'
        offset = url_for(controller='group', action='new')
        res = self.app.get(offset, status=200, extra_environ={'REMOTE_USER': 'russianfan'})
        assert 'New Group' in res, res
        fv = res.forms[0]
        assert fv[prefix+'name'].value == '', fv.fields
        fv[prefix+'name'] = group_name
        res = fv.submit('commit', status=302, extra_environ={'REMOTE_USER': 'russianfan'})
        res = res.follow()
        assert group_name in res, res
        assert 'No Title' in res, res
        model.Session.remove()

        # Create duplicate group
        group_name = u'testgrp1'
        offset = url_for(controller='group', action='new')
        res = self.app.get(offset, status=200, extra_environ={'REMOTE_USER': 'russianfan'})
        assert 'New Group' in res, res
        fv = res.forms[0]
        assert fv[prefix+'name'].value == '', fv.fields
        fv[prefix+'name'] = group_name
        res = fv.submit('commit', status=200, extra_environ={'REMOTE_USER': 'russianfan'})
        assert 'Group name already exists' in res, res
        self.check_tag(res, '<form', 'class="has-errors"')
        assert 'class="field_error"' in res, res
