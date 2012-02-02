import ckan.model as model
from ckan.tests import *
from ckan.lib.base import *
import ckan.authz as authz


def check_and_set_checkbox(theform, user, role, should_be, set_to):
   '''Given an authz form, find the checkbox associated with the strings user and role,
   assert that it\'s in the state 'should_be', and set it to 'set_to' '''
   user_id = (model.User.get(user) or model.AuthorizationGroup.get(user)).id
   user_role_string = '%s$%s' % (user_id, role)
   checkboxes = [x for x in theform.fields[user_role_string] \
                                   if x.__class__.__name__ == 'Checkbox']

   assert(len(checkboxes)==1), \
        "there should only be one checkbox for %s/%s" % (user, role)
   checkbox = checkboxes[0]

   #checkbox should be unticked
   assert checkbox.checked==should_be, \
                 "%s/%s checkbox in unexpected state" % (user, role)

   #tick or untick the box and return the form
   checkbox.checked=set_to
   return theform


class TestEditAuthz(TestController):
    @classmethod
    def setup_class(self):
        # for the authorization editing tests we set up test data so:
        # three users, sysadmin , administrator, and another
        # one authzgroup, one group, one package
        # and administrator is admin on all three
        # one extra authzgroup, authzgroup2, with no permissions to start with
        model.repo.init_db()
        model.repo.new_revision()
        
        self.sysadmin = 'sysadmin'
        sysadmin_user = model.User(name=unicode(self.sysadmin))
        self.admin = 'administrator'
        admin_user = model.User(name=unicode(self.admin))
        self.another = 'another'
        another_user = model.User(name=unicode(self.another))
        self.authzgroup = 'authzgroup'
        authzgroup = model.AuthorizationGroup(name=unicode(self.authzgroup))
        self.group = 'group'
        group = model.Group(name=unicode(self.group))
        self.authzgroup2 = 'authzgroup2'
        authzgroup2 = model.AuthorizationGroup(name=unicode(self.authzgroup2))


        for obj in sysadmin_user, admin_user, another_user, authzgroup, group, authzgroup2:
            model.Session.add(obj)

        model.add_user_to_role(sysadmin_user, model.Role.ADMIN, model.System())
        model.repo.commit_and_remove()

        model.repo.new_revision()

        self.pkg = u'dataset'
        pkg = model.Package(name=self.pkg)
        model.Session.add(pkg)

        admin_user = model.User.by_name(unicode(self.admin))
        assert admin_user

        # setup all three authorization objects to have logged in and visitor as editors, and the admin as admin
        model.setup_user_roles(pkg, ['editor'], ['editor'], [admin_user])
        model.setup_user_roles(authzgroup, ['editor'], ['editor'], [admin_user])
        model.setup_user_roles(group, ['editor'], ['editor'], [admin_user])

        model.repo.commit_and_remove()

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()

    def test_access_to_authz(self):
        #for each of the three authz pages, check that the access permissions work correctly
        for (c,i) in [('package', self.pkg),('group', self.group),('authorization_group', self.authzgroup)]:
            offset = url_for(controller=c, action='authz', id=i)

            # attempt to access the authz pages without credentials should result in getting redirected to the login page
            res = self.app.get(offset, status=[302])
            res = res.follow()
            assert res.request.url.startswith('/user/login')

            # for an ordinary user, it should result in access denied
            # which is weird, because in the app proper he'd get redirected too.
            # it behaves differently in the test setup, but this is a known strangeness.
            res = self.app.get(offset, status=[401], extra_environ={'REMOTE_USER':self.another})

            # going there as the package administrator or system administrator should be fine
            for u in [self.admin,self.sysadmin]:
                res = self.app.get(offset, status=[200], extra_environ={'REMOTE_USER':u})
                # the name of the object should appear in the page
                assert i in res
                assert "Authorization" in res, res


    def roles_list(self, authzobj):
        # get a list of username/roles for a given authorizable object
        list = [ (r.user.name, r.role) for r in authzobj.roles if r.user]
        list.extend([(r.authorized_group.name, r.role) for r in authzobj.roles if r.authorized_group])
        return list

    # get the users/roles for the specific objects created in our test data
    def package_roles(self):
        return self.roles_list(model.Package.by_name(self.pkg))

    def group_roles(self):
        return self.roles_list(model.Group.by_name(self.group))

    def authzgroup_roles(self):
        return self.roles_list(model.AuthorizationGroup.by_name(self.authzgroup))

    # check that the authz page for each object contains certain key strings
    def test_2_read_ok(self):
        for (c,i,m) in [('package', self.pkg, self.package_roles),\
                        ('group', self.group, self.group_roles),\
                        ('authorization_group', self.authzgroup, self.authzgroup_roles)]:
            offset = url_for(controller=c, action='authz', id=i)
            res = self.app.get(offset, extra_environ={'REMOTE_USER': self.admin})
            assert i in res, res
            assert "Authorization" in res, res

            # all the package's users and roles should appear in tables
            assert '<tr' in res
            for (user,role) in m():
                assert user in res
                assert role in res


    def assert_roles_to_be(self, actual_roles_list, expected_roles_list):
        # given an actual and an expected list of user/roles, assert that they're as expected, 
        # modulo ordering.
        ok = ( len(actual_roles_list) == len(expected_roles_list) )
        for r in actual_roles_list:
           if not r in expected_roles_list:
               ok = False
        if not ok:
           print "expected roles: ", expected_roles_list
           print "actual roles: ", actual_roles_list
           assert False, "roles not as expected"


    # check that when we change one role and add another, that both the checkbox states and the database
    # change as we expect them to, and that the roles on the other objects don't get changed by accident.
    # this should guard against certain errors which might be introduced by copy and pasting the controller code.
    def change_roles(self, user):

        normal_roles=[('administrator', 'admin'),
                      ('visitor', 'editor'),
                      ('logged_in', 'editor')]

        changed_roles=[('administrator', 'admin'),
                       ('visitor', 'editor'),
                       ('visitor', 'reader'),
                       ('logged_in', 'admin')]

        # loop variables here are the controller string, the name of the object we're changing, and three functions, 
        # the first fn gets the roles which we'd like to change, and the other two get the roles which we'd like to stay the same.
        for (c,i,var,const1,const2) in [('package', self.pkg, self.package_roles, self.group_roles, self.authzgroup_roles),\
                        ('group', self.group, self.group_roles, self.package_roles, self.authzgroup_roles),\
                        ('authorization_group', self.authzgroup, self.authzgroup_roles, self.package_roles, self.group_roles)]:

            # load authz page
            offset = url_for(controller=c, action='authz', id=i)
            res = self.app.get(offset, extra_environ={'REMOTE_USER':user})
            assert i in res

            self.assert_roles_to_be(var(), normal_roles)
            self.assert_roles_to_be(const1(), normal_roles)
            self.assert_roles_to_be(const2(), normal_roles)

            #admin makes visitor a reader and logged in an admin
            form = res.forms['theform']
            check_and_set_checkbox(form, u'visitor', u'reader', False, True)
            check_and_set_checkbox(form, u'logged_in', u'admin', False, True)
            check_and_set_checkbox(form, u'visitor', u'editor', True, True)
            check_and_set_checkbox(form, u'logged_in', u'editor', True, False)

            res = form.submit('save', extra_environ={'REMOTE_USER': user})

            # ensure db was changed
            self.assert_roles_to_be(var(), changed_roles)
            self.assert_roles_to_be(const1(), normal_roles)
            self.assert_roles_to_be(const2(), normal_roles)

            # ensure rerender of form is changed
            offset = url_for(controller=c, action='authz', id=i)
            res = self.app.get(offset, extra_environ={'REMOTE_USER':user})
            assert i in res

            # check that the checkbox states are what we think they should be
            # and put things back how they were.
            form = res.forms['theform']
            check_and_set_checkbox(form, u'visitor', u'reader', True, False)
            check_and_set_checkbox(form, u'logged_in', u'admin', True, False)
            check_and_set_checkbox(form, u'visitor', u'editor', True, True)
            check_and_set_checkbox(form, u'logged_in', u'editor', False, True)
            res = form.submit('save', extra_environ={'REMOTE_USER': user})

            # ensure db was changed
            self.assert_roles_to_be(var(), normal_roles)
            self.assert_roles_to_be(const1(), normal_roles)
            self.assert_roles_to_be(const2(), normal_roles)


    # do the change roles both as package/group/authzgroup admin, and also as sysadmin.
    def test_3_admin_changes_role(self):
        self.change_roles(self.admin)

    def test_3_sysadmin_changes_role(self):
        self.change_roles(self.sysadmin)

    def delete_role_as(self,user):

        normal_roles=[('administrator', 'admin'),
                      ('visitor', 'editor'),
                      ('logged_in', 'editor')]

        changed_roles=[('administrator', 'admin'),
                       ('logged_in', 'editor')]

        changed_roles2=[('administrator', 'admin'),
                        ('visitor', 'reader'),
                        ('logged_in', 'editor')]


        # loop variables here are the controller string, the name of the object we're changing, and three functions, 
        # the first fn gets the roles which we'd like to change, and the other two get the roles which we'd like to stay the same.
        for (c,i,var,const1,const2) in [('package', self.pkg, self.package_roles, self.group_roles, self.authzgroup_roles),\
                        ('group', self.group, self.group_roles, self.package_roles, self.authzgroup_roles),\
                        ('authorization_group', self.authzgroup, self.authzgroup_roles, self.package_roles, self.group_roles)]:

           # get the authz page, check that visitor's in there
           # remove visitor's role on the package
           # re-get the page and make sure that visitor's not in there at all
           offset = url_for(controller=c, action='authz', id=i)
           res = self.app.get(offset, extra_environ={'REMOTE_USER':user})
           assert self.pkg in res

           self.assert_roles_to_be(var(), normal_roles)
           self.assert_roles_to_be(const1(), normal_roles)
           self.assert_roles_to_be(const2(), normal_roles)

           assert 'visitor' in res
           assert 'administrator' in res
           assert 'logged_in' in res

           #admin removes visitor's only role
           form = res.forms['theform']
           check_and_set_checkbox(form, u'visitor', u'editor', True, False)
           res = form.submit('save', extra_environ={'REMOTE_USER': user})

           # ensure db was changed
           self.assert_roles_to_be(var(), changed_roles)
           self.assert_roles_to_be(const1(), normal_roles)
           self.assert_roles_to_be(const2(), normal_roles)

           # ensure rerender of form is changed
           offset = url_for(controller=c, action='authz', id=i)
           res = self.app.get(offset, extra_environ={'REMOTE_USER':user})
           assert self.pkg in res

           assert 'visitor' not in res
           assert 'administrator' in res
           assert 'logged_in' in res

           # check that the checkbox states are what we think they should be
           form = res.forms['theform']
           check_and_set_checkbox(form, u'logged_in', u'editor', True, True)
           check_and_set_checkbox(form, u'administrator', u'admin', True, True)

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
           assert 'administrator' in res
           assert 'logged_in' in res

           # check that the roles in the db are back to normal
           self.assert_roles_to_be(var(), changed_roles2)
           self.assert_roles_to_be(const1(), normal_roles)
           self.assert_roles_to_be(const2(), normal_roles)

           # now change him back to being an editor
           form = res.forms['theform']
           check_and_set_checkbox(form, u'visitor', u'reader', True, False)
           check_and_set_checkbox(form, u'visitor', u'editor', False, True)
           res = form.submit('save', extra_environ={'REMOTE_USER': user})

           # check that the page contains strings for everyone
           assert 'visitor' in res
           assert 'administrator' in res
           assert 'logged_in' in res

           # check that the roles in the db are back to normal
           self.assert_roles_to_be(var(), normal_roles)
           self.assert_roles_to_be(const1(), normal_roles)
           self.assert_roles_to_be(const2(), normal_roles)



    def test_4_admin_deletes_role(self):
        self.delete_role_as(self.admin)

    def test_4_sysadmin_deletes_role(self):
        self.delete_role_as(self.sysadmin)


    # now a version of the above tests dealing with permissions assigned to authzgroups 
    # (as opposed to on authzgroups)
    def add_change_delete_authzgroup_as(self, user):

        normal_roles=[('administrator', 'admin'),
                      ('visitor', 'editor'),
                      ('logged_in', 'editor')]

        changed_roles=[('authzgroup2', 'admin'),
                       ('administrator', 'admin'),
                       ('visitor', 'editor'),
                       ('logged_in', 'editor')]

        changed_roles_2=[('authzgroup2', 'editor'),
                         ('administrator', 'admin'),
                         ('visitor', 'editor'),
                         ('logged_in', 'editor')]

        for (c,i,var,const1,const2) in [('package', self.pkg, self.package_roles, self.group_roles, self.authzgroup_roles),\
                        ('group', self.group, self.group_roles, self.package_roles, self.authzgroup_roles),\
                        ('authorization_group', self.authzgroup, self.authzgroup_roles, self.package_roles, self.group_roles)]:

           # get the authz page, check that it contains the object name
           offset = url_for(controller=c, action='authz', id=i)
           res = self.app.get(offset, extra_environ={'REMOTE_USER':user})
           assert i in res

           # check the state of the database
           self.assert_roles_to_be(var(), normal_roles)
           self.assert_roles_to_be(const1(), normal_roles)
           self.assert_roles_to_be(const2(), normal_roles)

           # and that corresponding user strings are in the authz page
           # particularly that authzgroup2 isn't there (yet)
           assert 'visitor' in res
           assert 'administrator' in res
           assert 'logged_in' in res
           assert 'authzgroup2' not in res
 
           # add authzgroup2 as an admin
           form = res.forms['authzgroup_addform']
           form.fields['new_user_name'][0].value='authzgroup2'
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
           assert 'administrator' in res
           assert 'logged_in' in res
           assert 'authzgroup2' in res

           # and ensure that the database has changed as expected
           self.assert_roles_to_be(var(), changed_roles)
           self.assert_roles_to_be(const1(), normal_roles)
           self.assert_roles_to_be(const2(), normal_roles)
 
           # check that the checkbox states are what we think they should be
           # and change authzgroup2 from admin to editor
           form = res.forms['authzgroup_form']
           check_and_set_checkbox(form, u'authzgroup2', u'editor', False, True)
           check_and_set_checkbox(form, u'authzgroup2', u'admin', True, False)
           res = form.submit('authz_save', extra_environ={'REMOTE_USER': user})

           #check database has changed.
           self.assert_roles_to_be(var(), changed_roles_2)
           self.assert_roles_to_be(const1(), normal_roles)
           self.assert_roles_to_be(const2(), normal_roles)


           # now remove authzgroup2 entirely
           form = res.forms['authzgroup_form']
           check_and_set_checkbox(form, u'authzgroup2', u'editor', True, False)
           check_and_set_checkbox(form, u'authzgroup2', u'admin', False, False)
           res = form.submit('authz_save', extra_environ={'REMOTE_USER': user})

           #check database is back to normal
           self.assert_roles_to_be(var(), normal_roles)
           self.assert_roles_to_be(const1(), normal_roles)
           self.assert_roles_to_be(const2(), normal_roles)

           # and that page contains only the expected strings
           assert 'visitor' in res
           assert 'administrator' in res
           assert 'logged_in' in res
           assert 'authzgroup2' not in res


    def test_5_admin_changes_adds_deletes_authzgroup(self):
        self.add_change_delete_authzgroup_as(self.admin)

    def test_5_sysadmin_changes_adds_deletes_authzgroup(self):
        self.add_change_delete_authzgroup_as(self.sysadmin)
