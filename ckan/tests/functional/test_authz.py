import simplejson

import ckan.model as model
from ckan.tests import *
from ckan.lib.base import *
import ckan.authz as authz

class TestUsage(TestController2):
    @classmethod
    def _create_test_data(self):
        self.modes = ('--', 'r-', 'w-', 'rr', 'wr', 'ww') #  logged-in, visitor
        for mode in self.modes:
            model.Package(name=unicode(mode))
        model.User(name=u'testsysadmin') # in test.ini
        model.User(name=u'admin')
        model.User(name=u'editor')
        model.User(name=u'reader')
        model.User(name=u'mrloggedin')
        model.User(name=u'adminfriend')
        visitor_name = '123.12.12.123'
        rev = model.repo.new_revision()
        model.repo.commit_and_remove()

        testsysadmin = model.User.by_name(u'testsysadmin')
        admin = model.User.by_name(u'admin')
        editor = model.User.by_name(u'editor')
        reader = model.User.by_name(u'reader')
        mrloggedin = model.User.by_name(name=u'mrloggedin')
        visitor = model.User.by_name(name=model.PSEUDO_USER__VISITOR)
        for mode in self.modes:
            pkg = model.Package.by_name(unicode(mode))
            model.add_user_to_role(admin, model.Role.ADMIN, pkg)
            model.add_user_to_role(editor, model.Role.EDITOR, pkg)
            model.add_user_to_role(reader, model.Role.READER, pkg)
            if mode[0] == u'r':
                model.add_user_to_role(mrloggedin, model.Role.READER, pkg)
            if mode[0] == u'w':
                model.add_user_to_role(mrloggedin, model.Role.EDITOR, pkg)
            if mode[1] == u'r':
                model.add_user_to_role(visitor, model.Role.READER, pkg)
            if mode[1] == u'w':
                model.add_user_to_role(visitor, model.Role.EDITOR, pkg)
        model.repo.commit_and_remove()

        self.testsysadmin = model.User.by_name(u'testsysadmin')
        self.admin = model.User.by_name(u'admin')
        self.adminfriend = model.User.by_name(u'adminfriend')
        self.editor = model.User.by_name(u'editor')
        self.reader = model.User.by_name(u'reader')
        self.mrloggedin = model.User.by_name(name=u'mrloggedin')
        self.visitor = model.User.by_name(name=model.PSEUDO_USER__VISITOR)

    @classmethod
    def setup_class(self):
        self._create_test_data()
        model.Session.remove()

    @classmethod
    def teardown_class(self):
        model.Session.remove()
        model.repo.rebuild_db()
        model.Session.remove()

    def _do_test_wui(self, action, user, mode):
        # Test action on WUI
        offset = url_for(controller='package', action=action, id=unicode(mode))
        res = self.app.get(offset, extra_environ={'REMOTE_USER': user.name.encode('utf8')}, expect_errors=True)
        return mode in res and u'error' not in res and res.status==200

    def _do_test_rest(self, action, user, mode):
        # Test action on REST
        offset = '/api/rest/package/%s' % unicode(mode)
        if action == model.Action.EDIT:
            postparams = '%s=1' % simplejson.dumps({'title':u'newtitle'})
            func = self.app.post
        elif action == model.Action.READ:
            postparams = None
            func = self.app.get
        else:
            raise NotImplementedError
        res = func(offset, params=postparams,
                   extra_environ={'Authorization' : str(user.apikey)},
                   expect_errors=True)
        return mode in res and u'error' not in res and res.status==200
        
    def _test_can(self, action, user, modes):
        for i, mode in enumerate(modes):
            ok_wui = self._do_test_wui(action, user, mode)
            assert ok_wui, '(%i) Should be able to %r %r as user %r (WUI interface)' % (i, action, mode, user.name)
            ok_rest = self._do_test_rest(action, user, mode)
            assert ok_rest, '(%i) Should be able to %r %r as user %r (REST interface)' % (i, action, mode, user.name)

    def _test_cant(self, action, user, modes):
        for i, mode in enumerate(modes):
            ok_wui = self._do_test_wui(action, user, mode)
            assert not ok_wui, '(%i) Should NOT be able to %r %r as user %r (WUI interface)' % (i, action, mode, user.name)
            ok_rest = self._do_test_rest(action, user, mode)
            assert not ok_rest, '(%i) Should NOT be able to %r %r as user %r (REST interface)' % (i, action, mode, user.name)

    # Tests numbered by the use case

    def test_14_visitor_reads_stopped(self): 
        self._test_cant('read', self.visitor, ['--', 'r-', 'w-'])
    def test_01_visitor_reads(self): 
        self._test_can('read', self.visitor, ['rr', 'wr', 'ww'])

    def test_12_visitor_edits_stopped(self):
        self._test_cant('edit', self.visitor, ['--', 'r-', 'w-', 'rr', 'wr'])
    def test_02_visitor_edits(self):
        self._test_can('edit', self.visitor, ['ww'])

    def test_15_user_reads_stopped(self):
        self._test_cant('read', self.mrloggedin, ['--'])
    def test_03_user_reads(self):
        self._test_can('read', self.mrloggedin, ['r-', 'w-', 'rr', 'wr', 'ww'])

    def test_13_user_edits_stopped(self):
        self._test_cant('edit', self.mrloggedin, ['--', 'r-', 'rr'])
    def test_04_user_edits(self):
        self._test_can('edit', self.mrloggedin, ['w-', 'wr', 'ww'])

    def test_05_author_is_new_package_admin(self):
        user = self.mrloggedin
        
        # make new package
        assert not model.Package.by_name(u'annakarenina')
        offset = url_for(controller='package', action='new')
        res = self.app.get(offset, extra_environ={'REMOTE_USER': user.name.encode('utf8')})
        assert 'Packages - New' in res
        fv = res.forms[0]
        prefix = 'Package--'
        fv[prefix + 'name'] = 'annakarenina'
        res = fv.submit('commit', extra_environ={'REMOTE_USER': user.name.encode('utf8')})

        # check user is admin
        pkg = model.Package.by_name(u'annakarenina')
        assert pkg
        roles = authz.Authorizer().get_roles(user.name, pkg)
        assert model.Role.ADMIN in roles, roles
        roles = authz.Authorizer().get_roles(u'someoneelse', pkg)
        assert not model.Role.ADMIN in roles, roles

    def _get_authz_form(self, package_name, edit_user=None):
        assert not model.Package.by_name(package_name)
        pkg = model.Package(name=package_name)
        rev = model.repo.new_revision()
        model.repo.commit_and_remove()

        # package has default user roles
        pkg = model.Package.by_name(package_name)
        user = model.User.by_name(u'admin')    
        model.setup_default_user_roles(pkg, admins=[user])

        if edit_user:
            user = model.User.by_name(edit_user)

        # edit roles in WUI
        offset = url_for(controller='package', action='authz', id=pkg.name)
        res = self.app.get(offset, extra_environ={'REMOTE_USER': user.name.encode('utf8')})
        assert pkg.name in res
        assert '''<tr> <td>Anyone</td> <td><select id="0-role" name="0-role">
<option value="None"></option>
<option value="admin">Admin</option>
<option selected value="editor">Editor</option>
<option value="reader">Reader</option>
</select></td> </tr>''' in res, res
        assert '''<tr> <td><input id="2-username" name="2-username" type="text" value="admin"></td> <td><select id="2-role" name="2-role">
<option value="None"></option>
<option selected value="admin">Admin</option>
<option value="editor">Editor</option>
<option value="reader">Reader</option>
</select></td> </tr>''' in res, res
        assert 'submit' in res, res
        fv = res.forms[0]

        return user, fv

    def _edit_row(self, fv, pkg_name, user, row_index, old_name=None, old_role=None, new_name=None, new_role=None):
        username_name = '%i-username' % row_index
        dropdown_name = '%i-role' % row_index
        if old_name is not None:
            assert fv[username_name].value == old_name, fv[username_name].value
        if old_role is not None:
            assert fv[dropdown_name].value == old_role if old_role else 'None', fv[dropdown_name].value
        if new_name is not None:
            fv[username_name].value = new_name
        if new_role is not None:
            fv[dropdown_name].value = new_role if new_role else 'None'
        res = fv.submit('commit', extra_environ={'REMOTE_USER': user.name.encode('utf8')})
        assert 'Error' not in res, res

        # sent to package page
        res = res.follow()
        assert 'Package: %s' % pkg_name in res, res

        # go back to check values
        offset = url_for(controller='package', action='authz', id=pkg_name)
        res = self.app.get(offset)
        assert pkg_name in res
        if row_index == 0:
            new_name = 'Anyone'
        elif row_index == 1:
            new_name = 'Anyone logged in'
        row = '<tr> <td>%s</td> <td>%s</td> </tr>' % (new_name, new_role.capitalize())
        if new_role or row_index < 2:
            assert row in res, str(res) + repr(row)
        else:
            assert not row in res, str(res) + repr(row)
        return res

    def test_06_admin_authorizes_admin_for_package(self):
    ##6. An admin of a package adds a user as an admin
        pkg_name = u'test6'
        user, fv = self._get_authz_form(pkg_name)
        self._edit_row(fv, pkg_name, user, 3, '', 'None', 'adminfriend', 'admin')

    def test_07_admin_unauthorizes_package_admin(self):
    ##7. An admin of a package removes a user as an admin
        pkg_name = u'test7'
        user, fv = self._get_authz_form(pkg_name)
        self._edit_row(fv, pkg_name, user, 3, '', 'None', 'adminfriend', 'admin')
        self._edit_row(fv, pkg_name, user, 3, 'adminfriend', 'admin', 'adminfriend', '')

    def test_08_admin_authorizes_editor_for_package(self):
    ##8. Ditto for admin re. editor
        pkg_name = u'test8'
        user, fv = self._get_authz_form(pkg_name)
        self._edit_row(fv, pkg_name, user, 3, '', 'None', 'adminfriend', 'editor')

    ##TODO
    def test_09_admin_authorizes_reader_for_package(self):
    ##9. Ditto for admin re. reader
        pkg_name = u'test9'
        user, fv = self._get_authz_form(pkg_name)
        self._edit_row(fv, pkg_name, user, 3, '', 'None', 'adminfriend', 'reader')

    def test_10_admin_makes_visitors_and_users_readers(self):
    ##10. We wish to be able assign roles to 2 specific entire groups in addition to specific users: 'visitor', 'users'. These will be termed pseudo-users as we do not have AC 'groups' as such.
        pkg_name = u'test10'
        user, fv = self._get_authz_form(pkg_name)
        self._edit_row(fv, pkg_name, user, 0, None, 'editor', None, 'reader')
        res = self._edit_row(fv, pkg_name, user, 1, None, 'editor', None, 'reader')
        assert '<tr> <td>Anyone</td> <td>Reader</td> </tr>' in res, res
        assert '<tr> <td>Anyone logged in</td> <td>Reader</td> </tr>' in res, res

    def test_11_sysadmin_makes_authz_changes(self):
    ##11. The sysadmin alters the assignment of entities to roles for any package
        pkg_name = u'test11'
        user, fv = self._get_authz_form(pkg_name, edit_user=u'testsysadmin')
        self._edit_row(fv, pkg_name, user, 0, None, 'editor', None, 'reader')
