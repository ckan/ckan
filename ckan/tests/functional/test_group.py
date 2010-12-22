from ckan.tests import *
import ckan.model as model
from base import FunctionalTestCase

from ckan.plugins import SingletonPlugin, implements, IGroupController
from ckan import plugins

class MockGroupControllerPlugin(SingletonPlugin):
    implements(IGroupController)
    
    def __init__(self):
        from collections import defaultdict
        self.calls = defaultdict(int)
    
    def read(self, entity):
        self.calls['read'] += 1

    def create(self, entity):
        self.calls['create'] += 1

    def edit(self, entity):
        self.calls['edit'] += 1

    def authz_add_role(self, object_role):
        self.calls['authz_add_role'] += 1

    def authz_remove_role(self, object_role):
        self.calls['authz_remove_role'] += 1

    def delete(self, entity):
        self.calls['delete'] += 1

class TestGroup(FunctionalTestCase):

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
        assert 'Groups</a>' in res, res
        res = res.click(href='/group/', index=0)
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
        title = u'Dave\'s books'
        pkgname = u'warandpeace'
        offset = url_for(controller='group', action='read', id=name)
        res = self.app.get(offset)
        main_res = self.main_div(res)
        assert '%s - Groups' % title in res, res
        #assert 'edit' not in main_res, main_res
        assert 'Administrators:' in main_res, main_res
        assert 'russianfan' in main_res, main_res
        assert name in res, res
        assert 'There are 2 packages in this group' in self.strip_tags(main_res), main_res
        pkg = model.Package.by_name(pkgname)
        res = res.click(pkg.title)
        assert '%s - Data Packages' % pkg.title in res
        
    def test_read_plugin_hook(self):
        plugin = MockGroupControllerPlugin()
        plugins.load(plugin)
        name = u'david'
        offset = url_for(controller='group', action='read', id=name)
        res = self.app.get(offset, status=200, extra_environ={'REMOTE_USER': 'russianfan'})
        assert plugin.calls['read'] == 1, plugin.calls
        plugins.unload(plugin)

    def test_read_and_authorized_to_edit(self):
        name = u'david'
        title = u'Dave\'s books'
        pkgname = u'warandpeace'
        offset = url_for(controller='group', action='read', id=name)
        res = self.app.get(offset, extra_environ={'REMOTE_USER': 'russianfan'})
        assert '%s - Groups' % title in res, res
        assert 'edit' in res
        assert name in res

    def test_new(self):
        offset = url_for(controller='group')
        res = self.app.get(offset, extra_environ={'REMOTE_USER': 'russianfan'})
        assert 'Create a new group' in res, res
        

class TestEdit(FunctionalTestCase):
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
        assert 'Edit Group: %s' % self.groupname in res, res

        form = res.forms['group-edit']
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
        form['PackageGroup--package_name'] = pkg.name

        
        res = form.submit('save', status=302, extra_environ={'REMOTE_USER': 'russianfan'})
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
        offset = url_for(controller='package', action='autocomplete', q='an')
        res = self.app.get(offset, status=200, extra_environ={'REMOTE_USER': 'russianfan'})
        assert 'annakarenina' in res, res
        assert not 'newone' in res, res
        model.repo.new_revision()
        pkg = model.Package(name=u'anewone')
        model.Session.add(pkg)
        model.repo.commit_and_remove()

        model.repo.new_revision()
        pkg = model.Package.by_name(u'anewone')
        user = model.User.by_name(u'russianfan')
        model.setup_default_user_roles(pkg, [user])
        model.repo.commit_and_remove()
        
        res = self.app.get(offset, status=200, extra_environ={'REMOTE_USER': 'russianfan'})
        assert 'annakarenina' in res, res
        assert 'newone' in res
        
    def test_edit_plugin_hook(self):
        plugin = MockGroupControllerPlugin()
        plugins.load(plugin)
        offset = url_for(controller='group', action='edit', id=self.groupname)
        res = self.app.get(offset, status=200, extra_environ={'REMOTE_USER': 'russianfan'})
        form = res.forms['group-edit']
        group = model.Group.by_name(self.groupname)
        form['Group-%s-title' % group.id] = "huhuhu"
        res = form.submit('save', status=302, extra_environ={'REMOTE_USER': 'russianfan'})
        assert plugin.calls['edit'] == 1, plugin.calls
        plugins.unload(plugin)

class TestNew(FunctionalTestCase):
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
        fv = res.forms['group-edit']
        assert fv[prefix+'name'].value == '', fv.fields
        assert fv[prefix+'title'].value == ''
        assert fv[prefix+'description'].value == ''
        assert fv['PackageGroup--package_name'].value == '', fv['PackageGroup--package_name'].value

        # Edit form
        fv[prefix+'name'] = group_name
        fv[prefix+'title'] = group_title
        fv[prefix+'description'] = group_description
        pkg = model.Package.by_name(self.packagename)
        fv['PackageGroup--package_name'] = pkg.name
        res = fv.submit('save', status=302, extra_environ={'REMOTE_USER': 'russianfan'})
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
        fv = res.forms['group-edit']
        assert fv[prefix+'name'].value == '', fv.fields
        fv[prefix+'name'] = group_name
        res = fv.submit('save', status=302, extra_environ={'REMOTE_USER': 'russianfan'})
        res = res.follow()
        assert group_name in res, res
        assert 'No Title' in res, res
        model.Session.remove()

        # Create duplicate group
        group_name = u'testgrp1'
        offset = url_for(controller='group', action='new')
        res = self.app.get(offset, status=200, extra_environ={'REMOTE_USER': 'russianfan'})
        assert 'New Group' in res, res
        fv = res.forms['group-edit']
        assert fv[prefix+'name'].value == '', fv.fields
        fv[prefix+'name'] = group_name
        res = fv.submit('save', status=200, extra_environ={'REMOTE_USER': 'russianfan'})
        assert 'Group name already exists' in res, res
        self.check_tag(res, '<form', 'class="has-errors"')
        assert 'class="field_error"' in res, res
    
    def test_new_plugin_hook(self):
        plugin = MockGroupControllerPlugin()
        plugins.load(plugin)
        offset = url_for(controller='group', action='new')
        res = self.app.get(offset, status=200, extra_environ={'REMOTE_USER': 'russianfan'})
        form = res.forms['group-edit']
        form['Group--name'] = "hahaha"
        form['Group--title'] = "huhuhu"
        res = form.submit('save', status=302, extra_environ={'REMOTE_USER': 'russianfan'})
        assert plugin.calls['create'] == 1, plugin.calls
        plugins.unload(plugin)

class TestRevisions(FunctionalTestCase):
    @classmethod
    def setup_class(self):
        model.Session.remove()
        self.name = u'revisiontest1'

        # create pkg
        self.description = [u'Written by Puccini', u'Written by Rossini', u'Not written at all', u'Written again', u'Written off']
        rev = model.repo.new_revision()
        self.grp = model.Group(name=self.name)
        self.grp.description = self.description[0]
        model.Session.add(self.grp)
        model.setup_default_user_roles(self.grp)
        model.repo.commit_and_remove()

        # edit pkg
        for i in range(5)[1:]:
            rev = model.repo.new_revision()
            grp = model.Group.by_name(self.name)
            grp.description = self.description[i]
            model.repo.commit_and_remove()

        self.grp = model.Group.by_name(self.name)        

    @classmethod
    def teardown_class(self):
        self.purge_packages([self.name])

    def test_0_read_history(self):
        offset = url_for(controller='group', action='history', id=self.grp.name)
        res = self.app.get(offset)
        main_res = self.main_div(res)
        assert self.grp.name in main_res, main_res
        assert 'radio' in main_res, main_res
        latest_rev = self.grp.all_revisions[0]
        oldest_rev = self.grp.all_revisions[-1]
        first_radio_checked_html = '<input checked="checked" id="selected1_%s"' % latest_rev.revision_id
        assert first_radio_checked_html in main_res, '%s %s' % (first_radio_checked_html, main_res)
        last_radio_checked_html = '<input checked="checked" id="selected2_%s"' % oldest_rev.revision_id
        assert last_radio_checked_html in main_res, '%s %s' % (last_radio_checked_html, main_res)

    def test_1_do_diff(self):
        offset = url_for(controller='group', action='history', id=self.grp.name)
        res = self.app.get(offset)
        form = res.forms['group-revisions']
        res = form.submit()
        res = res.follow()
        main_res = self.main_div(res)
        assert 'error' not in main_res.lower(), main_res
        assert 'Revision Differences' in main_res, main_res
        assert self.grp.name in main_res, main_res
        assert '<tr><td>description</td><td><pre>- Written by Puccini\n+ Written off</pre></td></tr>' in main_res, main_res

    def test_2_atom_feed(self):
        offset = url_for(controller='group', action='history', id=self.grp.name)
        offset = "%s?format=atom" % offset
        res = self.app.get(offset)
        assert '<feed' in res, res
        assert 'xmlns="http://www.w3.org/2005/Atom"' in res, res
        assert '</feed>' in res, res

