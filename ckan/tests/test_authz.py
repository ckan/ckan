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
        model.Package(name=u'testpkg')
        model.Package(name=u'testpkg2')
        model.User(name=u'testadmin')
        model.User(name=u'testsysadmin') # in test.ini
        model.User(name=u'notadmin')
        model.repo.new_revision()
        model.repo.commit_and_remove()

        pkg = model.Package.by_name(u'testpkg')
        admin = model.User.by_name(u'testadmin')
        model.add_user_to_role(admin, model.Role.ADMIN, pkg)
        model.repo.commit_and_remove()

        self.authorizer = ckan.authz.Authorizer()
        self.pkg = model.Package.by_name(u'testpkg')
        self.pkg2 = model.Package.by_name(u'testpkg2')
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

    def test_sys_admin(self):
        action = model.Action.PURGE
        assert self.controller.is_authorized(self.sysadmin.name, action, self.pkg)
        assert self.controller.is_authorized(self.sysadmin.name, action, self.pkg2)
        assert not self.controller.is_authorized(u'blah', action, self.pkg)

    def test_blacklist_edit(self):
        action = model.Action.EDIT
        username = u'testadmin'
        bad_username = u'83.222.23.234'
        assert self.controller.is_authorized(self.admin.name, action, self.pkg)
        assert not self.controller.is_authorized(bad_username, action, self.pkg)
