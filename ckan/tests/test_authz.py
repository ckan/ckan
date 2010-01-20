import ckan.model as model
import ckan.authz

class TestBlacklister(object):

    def test_1(self):
        blacklister = ckan.authz.Blacklister()
        bad_username = u'83.222.23.234' # in test.ini
        good_username = u'124.168.141.31'
        good_username2 = u'testadmin'
        assert blacklister.is_blacklisted(bad_username)
        assert not blacklister.is_blacklisted(good_username)
        assert not blacklister.is_blacklisted(good_username2)


class TestAuthorizer(object):

    @classmethod
    def setup_class(self):
        model.Session.add(model.Package(name=u'testpkg'))
        model.Session.add(model.Package(name=u'testpkg2'))
        model.Session.add(model.User(name=u'testadmin'))
        model.Session.add(model.User(name=u'testsysadmin'))
        model.Session.add(model.User(name=u'notadmin'))
        model.Session.add(model.Group(name=u'testgroup'))
        model.Session.add(model.Group(name=u'testgroup2'))
        model.repo.new_revision()
        model.repo.commit_and_remove()

        pkg = model.Package.by_name(u'testpkg')
        grp = model.Group.by_name(u'testgroup')
        admin = model.User.by_name(u'testadmin')
        sysadmin = model.User.by_name(u'testsysadmin')
        model.add_user_to_role(admin, model.Role.ADMIN, pkg)
        model.add_user_to_role(admin, model.Role.ADMIN, grp)
        model.add_user_to_role(sysadmin, model.Role.ADMIN, model.System())
        model.repo.commit_and_remove()

        self.authorizer = ckan.authz.Authorizer()
        self.pkg = model.Package.by_name(u'testpkg')
        self.pkg2 = model.Package.by_name(u'testpkg2')
        self.grp = model.Group.by_name(u'testgroup')
        self.grp2 = model.Group.by_name(u'testgroup2')
        self.admin = model.User.by_name(u'testadmin')
        self.sysadmin = model.User.by_name(u'testsysadmin')
        self.notadmin = model.User.by_name(u'notadmin')

    @classmethod
    def teardown_class(self):
        model.Session.remove()
        model.repo.rebuild_db()
        model.Session.remove()

    controller = ckan.authz.Authorizer()

    def test_pkg_admin(self):
        action = model.Action.PURGE
        assert self.controller.is_authorized(self.admin.name, action, self.pkg)
        assert not self.controller.is_authorized(self.admin.name, action, self.pkg2)
        assert not self.controller.is_authorized(u'blah', action, self.pkg)

    def test_grp_admin(self):
        action = model.Action.PURGE
        assert self.controller.is_authorized(self.admin.name, action, self.grp)
        assert not self.controller.is_authorized(self.admin.name, action, self.grp2)
        assert not self.controller.is_authorized(u'blah', action, self.grp)

    def test_pkg_sys_admin(self):
        action = model.Action.PURGE
        assert self.controller.is_authorized(self.sysadmin.name, action, self.pkg)
        assert self.controller.is_authorized(self.sysadmin.name, action, self.pkg2)
        assert not self.controller.is_authorized(u'blah', action, self.pkg)

    def test_grp_sys_admin(self):
        action = model.Action.PURGE
        assert self.controller.is_authorized(self.sysadmin.name, action, self.grp)
        assert self.controller.is_authorized(self.sysadmin.name, action, self.grp2)
        assert not self.controller.is_authorized(u'blah', action, self.grp)

    def test_blacklist_edit_pkg(self):
        action = model.Action.EDIT
        username = u'testadmin'
        bad_username = u'83.222.23.234'
        assert self.controller.is_authorized(self.admin.name, action, self.pkg)
        assert not self.controller.is_authorized(bad_username, action, self.pkg)

    def test_blacklist_edit_grp(self):
        action = model.Action.EDIT
        username = u'testadmin'
        bad_username = u'83.222.23.234'
        assert self.controller.is_authorized(self.admin.name, action, self.grp)
        assert not self.controller.is_authorized(bad_username, action, self.grp)

    def test_revision_purge(self):
        action = model.Action.PURGE
        isa = self.controller.is_authorized(self.sysadmin.name, action,
                model.Revision)
        assert isa, isa
        isnot = self.controller.is_authorized(self.notadmin.name, action,
                model.Revision)
        assert not isnot, isnot


