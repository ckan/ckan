import re

from nose.tools import assert_equal
import mock

import ckan.model as model
import ckan.lib.search as search

from ckan.tests import setup_test_search_index
from ckan import plugins
from ckan.lib.create_test_data import CreateTestData
from ckan.logic import get_action
from ckan.tests import *
from base import FunctionalTestCase
from ckan.tests import is_search_supported


class TestGroup(FunctionalTestCase):

    @classmethod
    def setup_class(self):
        search.clear()
        model.Session.remove()
        CreateTestData.create()

        # reduce extraneous logging
        from ckan.lib import activity_streams_session_extension
        activity_streams_session_extension.logger.level = 100

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()

    def test_atom_feed_page_zero(self):
        group_name = 'deletetest'
        CreateTestData.create_groups([{'name': group_name,
                                       'packages': []}],
                                     admin_user_name='testsysadmin')

        offset = url_for(controller='feed', action='group',
                         id=group_name)
        offset = offset + '?page=0'
        res = self.app.get(offset)
        assert '<feed' in res, res
        assert 'xmlns="http://www.w3.org/2005/Atom"' in res, res
        assert '</feed>' in res, res

    def test_atom_feed_page_negative(self):
        group_name = 'deletetest'
        CreateTestData.create_groups([{'name': group_name,
                                       'packages': []}],
                                     admin_user_name='testsysadmin')

        offset = url_for(controller='feed', action='group',
                         id=group_name)
        offset = offset + '?page=-2'
        res = self.app.get(offset, expect_errors=True)
        assert '"page" parameter must be a positive integer' in res, res

    def test_children(self):
        if model.engine_is_sqlite():
            from nose import SkipTest
            raise SkipTest("Can't use CTE for sqlite")

        group_name = 'deletetest'
        CreateTestData.create_groups([{'name': group_name,
                                       'packages': []},
                                      {'name': "parent_group",
                                       'packages': []}],
                                     admin_user_name='testsysadmin')

        parent = model.Group.by_name("parent_group")
        group = model.Group.by_name(group_name)

        rev = model.repo.new_revision()
        rev.author = "none"

        member = model.Member(group_id=group.id, table_id=parent.id,
                              table_name='group', capacity='member')
        model.Session.add(member)
        model.repo.commit_and_remove()

        offset = url_for(controller='group', action='edit', id=group_name)
        res = self.app.get(offset, status=200,
                           extra_environ={'REMOTE_USER': 'testsysadmin'})
        main_res = self.main_div(res)
        assert 'Edit: %s' % group.title in main_res, main_res
        assert 'value="active" selected' in main_res, main_res

        parent = model.Group.by_name("parent_group")
        assert_equal(len(parent.get_children_groups()), 1)

        # delete
        form = res.forms['group-edit']
        form['state'] = 'deleted'
        res = form.submit('save', status=302,
                          extra_environ={'REMOTE_USER': 'testsysadmin'})

        group = model.Group.by_name(group_name)
        assert_equal(group.state, 'deleted')

        parent = model.Group.by_name("parent_group")
        assert_equal(len(parent.get_children_groups()), 0)

    def test_sorting(self):
        model.repo.rebuild_db()

        testsysadmin = model.User(name=u'testsysadmin')
        testsysadmin.sysadmin = True
        model.Session.add(testsysadmin)

        pkg1 = model.Package(name="pkg1")
        pkg2 = model.Package(name="pkg2")
        model.Session.add(pkg1)
        model.Session.add(pkg2)

        CreateTestData.create_groups([{'name': "alpha", 'packages': []},
                                      {'name': "beta",
                                       'packages': ["pkg1", "pkg2"]},
                                      {'name': "delta",
                                       'packages': ["pkg1"]},
                                      {'name': "gamma", 'packages': []}],
                                     admin_user_name='testsysadmin')

        context = {'model': model, 'session': model.Session,
                   'user': 'testsysadmin', 'for_view': True,
                   'with_private': False}
        data_dict = {'all_fields': True}
        results = get_action('group_list')(context, data_dict)
        assert results[0]['name'] == u'alpha', results[0]['name']
        assert results[-1]['name'] == u'gamma', results[-1]['name']

        # Test name reverse
        data_dict = {'all_fields': True, 'sort': 'name desc'}
        results = get_action('group_list')(context, data_dict)
        assert results[0]['name'] == u'gamma', results[0]['name']
        assert results[-1]['name'] == u'alpha', results[-1]['name']

        # Test packages reversed
        data_dict = {'all_fields': True, 'sort': 'packages desc'}
        results = get_action('group_list')(context, data_dict)
        assert results[0]['name'] == u'beta', results[0]['name']
        assert results[1]['name'] == u'delta', results[1]['name']

        # Test packages forward
        data_dict = {'all_fields': True, 'sort': 'packages asc'}
        results = get_action('group_list')(context, data_dict)
        assert results[-2]['name'] == u'delta', results[-2]['name']
        assert results[-1]['name'] == u'beta', results[-1]['name']

        # Default ordering for packages
        data_dict = {'all_fields': True, 'sort': 'packages'}
        results = get_action('group_list')(context, data_dict)
        assert results[0]['name'] == u'beta', results[0]['name']
        assert results[1]['name'] == u'delta', results[1]['name']

    def test_mainmenu(self):
        # the home page does a package search so have to skip this test if
        # search is not supported
        if not is_search_supported():
            from nose import SkipTest
            raise SkipTest("Search not supported")

        offset = url_for(controller='home', action='index')
        res = self.app.get(offset)
        assert 'Groups' in res, res
        assert 'Groups</a>' in res, res
        res = res.click(href='/group', index=0)
        assert "Dave's books" in res, res

    def test_index(self):
        offset = url_for(controller='group', action='index')
        res = self.app.get(offset)
        assert re.search('<h1(.*)>\s*Groups', res.body)
        groupname = 'david'
        group = model.Group.by_name(unicode(groupname))
        group_title = group.title
        group_packages_count = len(group.packages())
        group_description = group.description
        self.check_named_element(res, 'tr', group_title,
                                 group_packages_count,
                                 group_description)
        res = res.click(group_title)
        assert groupname in res

    def test_read_non_existent(self):
        name = u'group_does_not_exist'
        offset = url_for(controller='group', action='read', id=name)
        res = self.app.get(offset, status=404)

    def test_read_plugin_hook(self):
        plugins.load('test_group_plugin')
        name = u'david'
        offset = url_for(controller='group', action='read', id=name)
        res = self.app.get(offset, status=200,
                           extra_environ={'REMOTE_USER': 'testsysadmin'})
        p = plugins.get_plugin('test_group_plugin')
        assert p.calls['read'] == 1, p.calls
        plugins.unload('test_group_plugin')

    def test_read_and_authorized_to_edit(self):
        name = u'david'
        title = u'Dave\'s books'
        pkgname = u'warandpeace'
        offset = url_for(controller='group', action='read', id=name)
        res = self.app.get(offset,
                           extra_environ={'REMOTE_USER': 'testsysadmin'})
        assert title in res, res
        assert 'edit' in res
        assert name in res

    def test_new_page(self):
        offset = url_for(controller='group', action='new')
        res = self.app.get(offset,
                           extra_environ={'REMOTE_USER': 'testsysadmin'})
        assert 'Add A Group' in res, res


class TestGroupWithSearch(FunctionalTestCase):

    @classmethod
    def setup_class(self):
        setup_test_search_index()
        model.Session.remove()
        CreateTestData.create()

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()

    def test_read(self):
        # Relies on the search index being available
        name = u'david'
        title = u'Dave\'s books'
        pkgname = u'warandpeace'
        group = model.Group.by_name(name)
        for group_ref in (group.name, group.id):
            offset = url_for(controller='group', action='read', id=group_ref)
            res = self.app.get(offset)
            main_res = self.main_div(res)
            assert title in res, res
            #assert 'edit' not in main_res, main_res
           # Administrator no longer exists for the group due to auth changes
           # assert 'Administrators' in res, res
           # assert 'russianfan' in main_res, main_res
            assert name in res, res
            no_datasets_found = int(re.search('(\d*) datasets found',
                                    main_res).groups()[0])
            assert_equal(no_datasets_found, 2)
            pkg = model.Package.by_name(pkgname)
            res = res.click(pkg.title)
            assert '%s - Datasets' % pkg.title in res


class TestEdit(FunctionalTestCase):

    @classmethod
    def setup_class(self):
        setup_test_search_index()
        model.Session.remove()
        CreateTestData.create()
        self.groupname = u'david'
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

    def test_2_edit(self):
        group = model.Group.by_name(self.groupname)
        offset = url_for(controller='group', action='edit', id=self.groupname)
        print offset
        res = self.app.get(offset, status=200,
                           extra_environ={'REMOTE_USER': 'testsysadmin'})
        assert 'Edit: %s' % group.title in res, res

        form = res.forms['group-edit']
        titlefn = 'title'
        descfn = 'description'
        newtitle = 'xxxxxxx'
        newdesc = '''### Lots of stuff here

Ho ho ho
'''

        form[titlefn] = newtitle
        form[descfn] = newdesc
        pkg = model.Package.by_name(self.packagename)
        form['packages__2__name'] = pkg.name

        res = form.submit('save', status=302,
                          extra_environ={'REMOTE_USER': 'testsysadmin'})
        # should be read page
        # assert 'Groups - %s' % self.groupname in res, res

        model.Session.remove()
        group = model.Group.by_name(self.groupname)
        assert group.title == newtitle, group
        assert group.description == newdesc, group

        # now look at datasets
        assert len(group.packages()) == 3

    def test_3_edit_form_has_new_package(self):
        # check for dataset in autocomplete
        offset = url_for(controller='package', action='autocomplete', q='an')
        res = self.app.get(offset, status=200,
                           extra_environ={'REMOTE_USER': 'testsysadmin'})
        assert 'annakarenina' in res, res
        assert not 'newone' in res, res
        model.repo.new_revision()
        pkg = model.Package(name=u'anewone')
        model.Session.add(pkg)
        model.repo.commit_and_remove()

        model.repo.new_revision()
        pkg = model.Package.by_name(u'anewone')
        user = model.User.by_name(u'testsysadmin')
        model.setup_default_user_roles(pkg, [user])
        model.repo.commit_and_remove()

        res = self.app.get(offset, status=200,
                           extra_environ={'REMOTE_USER': 'testsysadmin'})
        assert 'annakarenina' in res, res
        assert 'newone' in res

    def test_4_new_duplicate_package(self):
        prefix = ''

        # Create group
        group_name = u'testgrp4'
        CreateTestData.create_groups([{'name': group_name,
                                       'packages': [self.packagename]}],
                                     admin_user_name='testsysadmin')

        # Add same package again
        offset = url_for(controller='group', action='edit', id=group_name)
        res = self.app.get(offset, status=200,
                           extra_environ={'REMOTE_USER': 'testsysadmin'})
        fv = res.forms['group-edit']
        fv['packages__1__name'] = self.packagename
        res = fv.submit('save', status=302,
                        extra_environ={'REMOTE_USER': 'testsysadmin'})
        res = res.follow()
        assert group_name in res, res
        model.Session.remove()

        # check package only added to the group once
        group = model.Group.by_name(group_name)
        pkg_names = [pkg.name for pkg in group.packages()]
        assert_equal(pkg_names, [self.packagename])

    def test_edit_plugin_hook(self):
        plugins.load('test_group_plugin')
        offset = url_for(controller='group', action='edit', id=self.groupname)
        res = self.app.get(offset, status=200,
                           extra_environ={'REMOTE_USER': 'testsysadmin'})
        form = res.forms['group-edit']
        group = model.Group.by_name(self.groupname)
        form['title'] = "huhuhu"
        res = form.submit('save', status=302,
                          extra_environ={'REMOTE_USER': 'testsysadmin'})
        p = plugins.get_plugin('test_group_plugin')
        assert p.calls['edit'] == 1, p.calls
        plugins.unload('test_group_plugin')

    def test_edit_image_url(self):
        group = model.Group.by_name(self.groupname)
        offset = url_for(controller='group', action='edit', id=self.groupname)
        res = self.app.get(offset, status=200,
                           extra_environ={'REMOTE_USER': 'testsysadmin'})

        form = res.forms['group-edit']
        image_url = u'http://url.to/image_url'
        form['image_url'] = image_url
        res = form.submit('save', status=302,
                          extra_environ={'REMOTE_USER': 'testsysadmin'})

        model.Session.remove()
        group = model.Group.by_name(self.groupname)
        assert group.image_url == image_url, group

    def test_edit_change_name(self):
        group = model.Group.by_name(self.groupname)
        offset = url_for(controller='group', action='edit', id=self.groupname)
        res = self.app.get(offset, status=200,
                           extra_environ={'REMOTE_USER': 'testsysadmin'})
        assert 'Edit: %s' % group.title in res, res

        def update_group(res, name, with_pkg=True):
            form = res.forms['group-edit']
            titlefn = 'title'
            descfn = 'description'
            newtitle = 'xxxxxxx'
            newdesc = '''### Lots of stuff here

    Ho ho ho
    '''
            form[titlefn] = newtitle
            form[descfn] = newdesc
            form['name'] = name
            if with_pkg:
                pkg = model.Package.by_name(self.packagename)
                form['packages__2__name'] = pkg.name

            res = form.submit('save', status=302,
                              extra_environ={'REMOTE_USER': 'testsysadmin'})
        update_group(res, self.groupname, True)
        update_group(res, 'newname', False)

        model.Session.remove()
        group = model.Group.by_name('newname')

        # We have the datasets in the DB, but we should also see that many
        # on the group read page.
        assert len(group.packages()) == 3

        offset = url_for(controller='group', action='read', id='newname')
        res = self.app.get(offset, status=200,
                           extra_environ={'REMOTE_USER': 'testsysadmin'})

        ds = res.body
        ds = ds[ds.index('datasets') - 10: ds.index('datasets') + 10]
        assert '3 datasets found' in res, ds

        # reset the group to how we found it
        offset = url_for(controller='group', action='edit', id='newname')
        res = self.app.get(offset, status=200,
                           extra_environ={'REMOTE_USER': 'testsysadmin'})

        update_group(res, self.groupname, True)

    def test_edit_non_existent(self):
        name = u'group_does_not_exist'
        offset = url_for(controller='group', action='edit', id=name)
        res = self.app.get(offset, status=404)

    def test_delete(self):
        group_name = 'deletetest'
        CreateTestData.create_groups([{'name': group_name,
                                       'packages': [self.packagename]}],
                                     admin_user_name='testsysadmin')

        group = model.Group.by_name(group_name)
        offset = url_for(controller='group', action='edit', id=group_name)
        res = self.app.get(offset, status=200,
                           extra_environ={'REMOTE_USER': 'testsysadmin'})
        main_res = self.main_div(res)
        assert 'Edit: %s' % group.title in main_res, main_res
        assert 'value="active" selected' in main_res, main_res

        # delete
        form = res.forms['group-edit']
        form['state'] = 'deleted'
        res = form.submit('save', status=302,
                          extra_environ={'REMOTE_USER': 'testsysadmin'})

        group = model.Group.by_name(group_name)
        assert_equal(group.state, 'deleted')
        res = self.app.get(offset, status=302)
        res = res.follow()
        assert res.request.url.startswith('/user/login'), res.request.url


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
        prefix = ''
        group_name = u'testgroup'
        group_title = u'Test Title'
        group_description = u'A Description'

        # Open 'Add A Group' page
        offset = url_for(controller='group', action='new')
        res = self.app.get(offset, status=200,
                           extra_environ={'REMOTE_USER': 'testsysadmin'})
        assert 'Add A Group' in res, res
        fv = res.forms['group-edit']
        assert fv[prefix + 'name'].value == '', fv.fields
        assert fv[prefix + 'title'].value == ''
        assert fv[prefix + 'description'].value == ''
        assert fv['packages__0__name'].value == '', \
            fv['Member--package_name'].value

        # Edit form
        fv[prefix + 'name'] = group_name
        fv[prefix + 'title'] = group_title
        fv[prefix + 'description'] = group_description
        pkg = model.Package.by_name(self.packagename)
        fv['packages__0__name'] = pkg.name
        res = fv.submit('save', status=302,
                        extra_environ={'REMOTE_USER': 'testsysadmin'})
        res = res.follow()
        assert '%s' % group_title in res, res

        model.Session.remove()
        group = model.Group.by_name(group_name)
        assert group.title == group_title, group
        assert group.description == group_description, group
        assert len(group.packages()) == 1
        pkg = model.Package.by_name(self.packagename)
        assert group.packages() == [pkg]

    def test_3_new_duplicate_group(self):
        prefix = ''

        # Create group
        group_name = u'testgrp1'
        offset = url_for(controller='group', action='new')
        res = self.app.get(offset, status=200,
                           extra_environ={'REMOTE_USER': 'testsysadmin'})
        assert 'Add A Group' in res, res
        fv = res.forms['group-edit']
        assert fv[prefix + 'name'].value == '', fv.fields
        fv[prefix + 'name'] = group_name
        res = fv.submit('save', status=302,
                        extra_environ={'REMOTE_USER': 'testsysadmin'})
        res = res.follow()
        assert group_name in res, res
        model.Session.remove()

        # Create duplicate group
        group_name = u'testgrp1'
        offset = url_for(controller='group', action='new')
        res = self.app.get(offset, status=200,
                           extra_environ={'REMOTE_USER': 'testsysadmin'})
        assert 'Add A Group' in res, res
        fv = res.forms['group-edit']
        assert fv[prefix + 'name'].value == '', fv.fields
        fv[prefix + 'name'] = group_name
        res = fv.submit('save', status=200,
                        extra_environ={'REMOTE_USER': 'testsysadmin'})
        assert 'Group name already exists' in res, res
        self.check_tag(res, '<form', 'has-errors')
        assert 'class="field_error"' in res, res

    def test_new_plugin_hook(self):
        plugins.load('test_group_plugin')
        offset = url_for(controller='group', action='new')
        res = self.app.get(offset, status=200,
                           extra_environ={'REMOTE_USER': 'testsysadmin'})
        form = res.forms['group-edit']
        form['name'] = "hahaha"
        form['title'] = "huhuhu"
        res = form.submit('save', status=302,
                          extra_environ={'REMOTE_USER': 'testsysadmin'})
        p = plugins.get_plugin('test_group_plugin')
        assert p.calls['create'] == 1, p.calls
        plugins.unload('test_group_plugin')

    def test_new_bad_param(self):
        offset = url_for(controller='group', action='new',
                         __bad_parameter='value')
        res = self.app.post(offset, {'save': '1'},
                            extra_environ={'REMOTE_USER': 'testsysadmin'},
                            status=400)
        assert 'Integrity Error' in res.body


class TestRevisions(FunctionalTestCase):
    @classmethod
    def setup_class(self):
        model.Session.remove()
        CreateTestData.create()
        self.name = u'revisiontest1'

        # create pkg
        self.description = [u'Written by Puccini', u'Written by Rossini',
                            u'Not written at all', u'Written again',
                            u'Written off']
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
        model.repo.rebuild_db()

    def test_0_read_history(self):
        offset = url_for(controller='group', action='history',
                         id=self.grp.name)
        res = self.app.get(offset)
        main_res = self.main_div(res)
        assert self.grp.name in main_res, main_res
        assert 'radio' in main_res, main_res
        latest_rev = self.grp.all_revisions[0]
        oldest_rev = self.grp.all_revisions[-1]
        first_radio_checked_html = \
            '<input checked="checked" id="selected1_%s"' % \
            latest_rev.revision_id
        assert first_radio_checked_html in main_res, '%s %s' % \
            (first_radio_checked_html, main_res)
        last_radio_checked_html = \
            '<input checked="checked" id="selected2_%s"' % \
            oldest_rev.revision_id
        assert last_radio_checked_html in main_res, '%s %s' % \
            (last_radio_checked_html, main_res)

    def test_1_do_diff(self):
        offset = url_for(controller='group', action='history',
                         id=self.grp.name)
        res = self.app.get(offset)
        form = res.forms['group-revisions']
        res = form.submit()
        res = res.follow()
        main_res = self.main_div(res)
        assert 'form-errors' not in main_res.lower(), main_res
        assert 'Revision Differences' in main_res, main_res
        assert self.grp.name in main_res, main_res
        assert "<tr><td>description</td><td><pre>- Written by Puccini\n+" + \
               " Written off</pre></td></tr>" in main_res, main_res

    def test_2_atom_feed(self):
        offset = url_for(controller='group', action='history',
                         id=self.grp.name)
        offset = "%s?format=atom" % offset
        res = self.app.get(offset)
        assert '<feed' in res, res
        assert 'xmlns="http://www.w3.org/2005/Atom"' in res, res
        assert '</feed>' in res, res


class TestMemberInvite(FunctionalTestCase):
    @classmethod
    def setup_class(self):
        model.Session.remove()
        model.repo.rebuild_db()

    def teardown(self):
        model.repo.rebuild_db()

    @mock.patch('ckan.lib.mailer.mail_user')
    def test_member_new_invites_user_if_received_email(self, mail_user):
        user = CreateTestData.create_user('a_user', sysadmin=True)
        group_name = 'a_group'
        CreateTestData.create_groups([{'name': group_name}], user.name)
        group = model.Group.get(group_name)
        url = url_for(controller='group', action='member_new', id=group.id)
        email = 'invited_user@mailinator.com'
        role = 'member'

        params = {'email': email, 'role': role}
        res = self.app.post(url, params,
                            extra_environ={'REMOTE_USER': str(user.name)})

        users = model.User.by_email(email)
        assert len(users) == 1, users
        user = users[0]
        assert user.email == email, user
        assert group.id in user.get_group_ids(capacity=role)
