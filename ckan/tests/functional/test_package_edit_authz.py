import ckan.model as model
from ckan.tests import *
from ckan.lib.base import *
import ckan.authz as authz
from test_edit_authz import check_and_set_checkbox


class TestPackageEditAuthz(TestController):
    @classmethod
    def setup_class(self):
        # for the authorization editing tests we set up test data so:
        # three users, madeup-sysadmin , madeup-administrator, and madeup-another
        # one authzgroup
        # two packages test6 and test6a, m-a is admin on both
        model.repo.init_db()
        model.repo.new_revision()
        
        self.sysadmin = 'madeup-sysadmin'
        sysadmin_user = model.User(name=unicode(self.sysadmin))
        self.admin = 'madeup-administrator'
        admin_user = model.User(name=unicode(self.admin))
        self.another = u'madeup-another'
        another_user = model.User(name=unicode(self.another))
        self.authzgroup = u'madeup-authzgroup'
        authzgroup = model.AuthorizationGroup(name=unicode(self.authzgroup))
        for obj in sysadmin_user, admin_user, another_user, authzgroup:
            model.Session.add(obj)

        model.add_user_to_role(sysadmin_user, model.Role.ADMIN, model.System())
        model.repo.new_revision()

        self.pkgname = u'test6'
        self.pkgname2 = u'test6a'
        pkg = model.Package(name=self.pkgname)
        pkg2 = model.Package(name=self.pkgname2)
        model.Session.add(pkg)
        model.Session.add(pkg2)
        admin_user = model.User.by_name(unicode(self.admin))
        assert admin_user
        model.setup_default_user_roles(pkg, admins=[admin_user])
        model.setup_default_user_roles(pkg2, admins=[admin_user])

        model.repo.commit_and_remove()

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()

    def test_0_nonadmin_cannot_edit_authz(self):
        offset = url_for(controller='package', action='authz', id=self.pkgname)
        res = self.app.get(offset, status=[302, 401])
        res = res.follow()
        assert res.request.url.startswith('/user/login')
     
    def test_1_admin_has_access(self):
        offset = url_for(controller='package', action='authz', id=self.pkgname)
        res = self.app.get(offset, extra_environ={'REMOTE_USER':
            self.admin})

    def test_1_sysadmin_has_access(self):
        offset = url_for(controller='package', action='authz', id=self.pkgname)
        res = self.app.get(offset, extra_environ={'REMOTE_USER':
            self.sysadmin})
    
    def test_2_read_ok(self):
        offset = url_for(controller='package', action='authz', id=self.pkgname)
        res = self.app.get(offset, extra_environ={'REMOTE_USER':
            self.admin})
        assert self.pkgname in res

        # all the package\'s users and roles should appear in tables
        assert '<tr' in res
        for (user,role) in self.package_roles():
            assert user in res
            assert role in res


    def package_roles(self):
        pkg = model.Package.by_name(self.pkgname)
        list = [ (r.user.name, r.role) for r in pkg.roles if r.user]
        list.extend([(r.authorized_group.name, r.role) for r in pkg.roles if r.authorized_group])
        return list

    def assert_package_roles_to_be(self, roles_list):
        prs=self.package_roles()
        ok = ( len(prs) == len(roles_list) )
        for r in roles_list:
           if not r in prs:
               ok = False
        if not ok:
           print "expected roles: ", roles_list
           print "actual roles: ", prs
           assert False, "roles not as expected"

    def change_roles(self, user):
        # load authz page
        offset = url_for(controller='package', action='authz', id=self.pkgname)
        res = self.app.get(offset, extra_environ={'REMOTE_USER':user})
        assert self.pkgname in res

        self.assert_package_roles_to_be([
           ('madeup-administrator', 'admin'),
           ('visitor', 'editor'),
           ('logged_in', 'editor')])

        #admin makes visitor a reader and logged in an admin
        form = res.forms['theform']
        check_and_set_checkbox(form, u'visitor', u'reader', False, True)
        check_and_set_checkbox(form, u'logged_in', u'admin', False, True)
        check_and_set_checkbox(form, u'visitor', u'editor', True, True)
        check_and_set_checkbox(form, u'logged_in', u'editor', True, False)

        res = form.submit('save', extra_environ={'REMOTE_USER': user})

        # ensure db was changed
        self.assert_package_roles_to_be([
           ('madeup-administrator', 'admin'),
           ('visitor', 'editor'),
           ('visitor', 'reader'),
           ('logged_in', 'admin')])

        # ensure rerender of form is changed
        offset = url_for(controller='package', action='authz', id=self.pkgname)
        res = self.app.get(offset, extra_environ={'REMOTE_USER':user})
        assert self.pkgname in res

        # check that the checkbox states are what we think they should be
        # and put things back how they were.
        form = res.forms['theform']
        check_and_set_checkbox(form, u'visitor', u'reader', True, False)
        check_and_set_checkbox(form, u'logged_in', u'admin', True, False)
        check_and_set_checkbox(form, u'visitor', u'editor', True, True)
        check_and_set_checkbox(form, u'logged_in', u'editor', False, True)
        res = form.submit('save', extra_environ={'REMOTE_USER': user})

        # ensure db was changed
        self.assert_package_roles_to_be([
           ('madeup-administrator', 'admin'),
           ('visitor', 'editor'),
           ('logged_in', 'editor')])


    def test_3_admin_changes_role(self):
        self.change_roles(self.admin)

    def test_3_sysadmin_changes_role(self):
        self.change_roles(self.sysadmin)

    def delete_role_as(self,user):
        # get the authz page, check that visitor's in there
        # remove visitor's role on the package
        # re-get the page and make sure that visitor's not in there at all
        offset = url_for(controller='package', action='authz', id=self.pkgname)
        res = self.app.get(offset, extra_environ={'REMOTE_USER':user})
        assert self.pkgname in res

        self.assert_package_roles_to_be([
           ('madeup-administrator', 'admin'),
           ('visitor', 'editor'),
           ('logged_in', 'editor')])

        assert 'visitor' in res
        assert 'madeup-administrator' in res
        assert 'logged_in' in res

        #admin removes visitor's only role
        form = res.forms['theform']
        check_and_set_checkbox(form, u'visitor', u'editor', True, False)
        res = form.submit('save', extra_environ={'REMOTE_USER': user})

        # ensure db was changed
        self.assert_package_roles_to_be([
           ('madeup-administrator', 'admin'),
           ('logged_in', 'editor')])

        # ensure rerender of form is changed
        offset = url_for(controller='package', action='authz', id=self.pkgname)
        res = self.app.get(offset, extra_environ={'REMOTE_USER':user})
        assert self.pkgname in res

        assert 'visitor' not in res
        assert 'madeup-administrator' in res
        assert 'logged_in' in res

        # check that the checkbox states are what we think they should be
        form = res.forms['theform']
        check_and_set_checkbox(form, u'logged_in', u'editor', True, True)
        check_and_set_checkbox(form, u'madeup-administrator', u'admin', True, True)

        # now we should add visitor back in, let's make him a reader
        form = res.forms['addform']
        form.fields['new_user_name'][0].value='visitor'
        checkbox = [x for x in form.fields['reader'] \
                      if x.__class__.__name__ == 'Checkbox'][0]
        # check it's currently unticked
        assert checkbox.checked == False
        # tick it and submit
        checkbox.checked=True
        res = form.submit('add', extra_environ={'REMOTE_USER':user})
        assert "User role(s) added" in res, "don't see flash message"

       # check that the page contains strings for everyone
        assert 'visitor' in res
        assert 'madeup-administrator' in res
        assert 'logged_in' in res

        # check that the roles in the db are back to normal
        self.assert_package_roles_to_be([
           ('madeup-administrator', 'admin'),
           ('visitor', 'reader'),
           ('logged_in', 'editor')])

        # now change him back to being an editor
        form = res.forms['theform']
        check_and_set_checkbox(form, u'visitor', u'reader', True, False)
        check_and_set_checkbox(form, u'visitor', u'editor', False, True)
        res = form.submit('save', extra_environ={'REMOTE_USER': user})
 
        # check that the page contains strings for everyone
        assert 'visitor' in res
        assert 'madeup-administrator' in res
        assert 'logged_in' in res

        # check that the roles in the db are back to normal
        self.assert_package_roles_to_be([
           ('madeup-administrator', 'admin'),
           ('visitor', 'editor'),
           ('logged_in', 'editor')])


    def test_4_admin_deletes_role(self):
        self.delete_role_as(self.admin)

    def test_4_sysadmin_deletes_role(self):
        self.delete_role_as(self.sysadmin)


    def test_5_add_change_delete_authzgroup(self):
        user=self.admin

        # get the authz page, check that authzgroup isn't in there
        offset = url_for(controller='package', action='authz', id=self.pkgname)
        res = self.app.get(offset, extra_environ={'REMOTE_USER':user})
        assert self.pkgname in res

        # check the state of the database
        self.assert_package_roles_to_be([
           ('madeup-administrator', 'admin'),
           ('visitor', 'editor'),
           ('logged_in', 'editor')])

        # and that corresponding user strings are in the authz page
        assert 'visitor' in res
        assert 'madeup-administrator' in res
        assert 'logged_in' in res
        assert 'madeup-authzgroup' not in res

        # add madeup-authzgroup as an admin
        form = res.forms['authzgroup_addform']
        form.fields['new_user_name'][0].value='madeup-authzgroup'
        checkbox = [x for x in form.fields['admin'] \
                      if x.__class__.__name__ == 'Checkbox'][0]
        # check the checkbox is currently unticked
        assert checkbox.checked == False
        # tick it and submit
        checkbox.checked=True
        res = form.submit('authz_add', extra_environ={'REMOTE_USER':user})
        assert "User role(s) added" in res, "don't see flash message"

        # examine the new page for user names/authzgroup names
        assert 'visitor' in res
        assert 'madeup-administrator' in res
        assert 'logged_in' in res
        assert 'madeup-authzgroup' in res

        # and ensure that the database has changed as expected
        self.assert_package_roles_to_be([
           ('madeup-authzgroup', 'admin'),
           ('madeup-administrator', 'admin'),
           ('visitor', 'editor'),
           ('logged_in', 'editor')])

        # check that the checkbox states are what we think they should be
        # and change madeup-authzgroup from admin to editor
        form = res.forms['authzgroup_form']
        check_and_set_checkbox(form, u'madeup-authzgroup', u'editor', False, True)
        check_and_set_checkbox(form, u'madeup-authzgroup', u'admin', True, False)
        res = form.submit('authz_save', extra_environ={'REMOTE_USER': user})

        #check database has changed.
        self.assert_package_roles_to_be([
           ('madeup-authzgroup', 'editor'),
           ('madeup-administrator', 'admin'),
           ('visitor', 'editor'),
           ('logged_in', 'editor')])

        # now remove madeup-authzgroup entirely
        form = res.forms['authzgroup_form']
        check_and_set_checkbox(form, u'madeup-authzgroup', u'editor', True, False)
        check_and_set_checkbox(form, u'madeup-authzgroup', u'admin', False, False)
        res = form.submit('authz_save', extra_environ={'REMOTE_USER': user})

        #check database is back to normal
        self.assert_package_roles_to_be([
           ('madeup-administrator', 'admin'),
           ('visitor', 'editor'),
           ('logged_in', 'editor')])

        # and that page contains only the expected strings
        assert 'visitor' in res
        assert 'madeup-administrator' in res
        assert 'logged_in' in res
        assert 'madeup-authzgroup' not in res
