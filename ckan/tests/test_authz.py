import sqlalchemy as sa
from pylons import config
from nose.tools import make_decorator, assert_equal

import ckan.model as model
import ckan.authz
from ckan import plugins
from ckan.model import Role
from ckan.tests import *


def uses_example_auth_plugin(func):
    def decorate(func):
        def wrapper(*args, **kwargs):
            def _plugin_setup():
                from ckan.tests.test_plugins import install_ckantestplugin
                _saved_plugins_config = config.get('ckan.plugins', '')
                install_ckantestplugin()
                config['ckan.plugins'] = 'authorizer_plugin'
                plugins.load_all(config)
                return _saved_plugins_config

            def _plugin_teardown(_saved_plugins_config):
                plugins.unload_all()
                config['ckan.plugins'] = _saved_plugins_config
                plugins.load_all(config)
            _saved_plugins_config = _plugin_setup()
            func(*args, **kwargs)
            _plugin_teardown(_saved_plugins_config)
        wrapper = make_decorator(func)(wrapper)
        return wrapper
    return decorate(func)

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
        CreateTestData.create()
        model.repo.new_revision()
        model.Session.add(model.Package(name=u'testpkg'))
        model.Session.add(model.Package(name=u'testpkg2'))
        model.Session.add(model.Package(name=u'private_pkg'))
        model.Session.add(model.User(name=u'testadmin'))
        # Cannot setup testsysadmin user as it is alreade done in
        # the default test data.
        #model.Session.add(model.User(name=u'testsysadmin')) 
        model.Session.add(model.User(name=u'notadmin'))
        model.Session.add(model.Group(name=u'testgroup'))
        model.Session.add(model.Group(name=u'testgroup2'))
        model.repo.commit_and_remove()

        model.repo.new_revision()
        pkg = model.Package.by_name(u'testpkg')
        pkg2 = model.Package.by_name(u'testpkg2')
        private_pkg = model.Package.by_name(u'private_pkg')
        pkg.add_relationship(u'depends_on', pkg2)
        pkg.add_relationship(u'depends_on', private_pkg)
        model.repo.commit_and_remove()

        pkg = model.Package.by_name(u'testpkg')
        grp = model.Group.by_name(u'testgroup')
        admin = model.User.by_name(u'testadmin')
        sysadmin = model.User.by_name(u'testsysadmin')
        notadmin = model.User.by_name(u'notadmin')
        model.add_user_to_role(admin, model.Role.ADMIN, pkg)
        model.add_user_to_role(admin, model.Role.ADMIN, grp)
        model.add_user_to_role(sysadmin, model.Role.ADMIN, model.System())
        model.add_user_to_role(notadmin, model.Role.READER, pkg)
        model.add_user_to_role(notadmin, model.Role.READER, pkg2)
        model.repo.commit_and_remove()

        self.authorizer = ckan.authz.Authorizer()
        self.pkg = model.Package.by_name(u'testpkg')
        self.pkg2 = model.Package.by_name(u'testpkg2')
        self.private_pkg = model.Package.by_name(u'private_pkg')
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

    authorizer = ckan.authz.Authorizer()

    def test_pkg_admin(self):
        action = model.Action.PURGE
        assert self.authorizer.is_authorized(self.admin.name, action, self.pkg)
        assert not self.authorizer.is_authorized(self.admin.name, action, self.pkg2)
        assert not self.authorizer.is_authorized(u'blah', action, self.pkg)

    @uses_example_auth_plugin
    def test_pkg_admin_with_plugin(self):
        action = model.Action.PURGE
        assert self.authorizer.is_authorized(self.notadmin.name,
                                             action,
                                             self.pkg2)

    def test_grp_admin(self):
        action = model.Action.PURGE
        assert self.authorizer.is_authorized(self.admin.name, action, self.grp)
        assert not self.authorizer.is_authorized(self.admin.name, action, self.grp2)
        assert not self.authorizer.is_authorized(u'blah', action, self.grp)

    def test_pkg_sys_admin(self):
        action = model.Action.PURGE
        assert self.authorizer.is_authorized(self.sysadmin.name, action, self.pkg)
        assert self.authorizer.is_authorized(self.sysadmin.name, action, self.pkg2)
        assert not self.authorizer.is_authorized(u'blah', action, self.pkg)

    def test_grp_sys_admin(self):
        action = model.Action.PURGE
        assert self.authorizer.is_authorized(self.sysadmin.name, action, self.grp)
        assert self.authorizer.is_authorized(self.sysadmin.name, action, self.grp2)
        assert not self.authorizer.is_authorized(u'blah', action, self.grp)

    def test_blacklist_edit_pkg(self):
        action = model.Action.EDIT
        username = u'testadmin'
        bad_username = u'83.222.23.234'
        assert self.authorizer.is_authorized(self.admin.name, action, self.pkg)
        assert not self.authorizer.is_authorized(bad_username, action, self.pkg)

    def test_blacklist_edit_grp(self):
        action = model.Action.EDIT
        username = u'testadmin'
        bad_username = u'83.222.23.234'
        assert self.authorizer.is_authorized(self.admin.name, action, self.grp)
        assert not self.authorizer.is_authorized(bad_username, action, self.grp)

    def test_revision_purge(self):
        action = model.Action.PURGE
        isa = self.authorizer.is_authorized(self.sysadmin.name, action,
                model.Revision)
        assert isa, isa
        isnot = self.authorizer.is_authorized(self.notadmin.name, action,
                model.Revision)
        assert not isnot, isnot

    def test_authorized_query(self):
        assert self.authorizer.is_authorized(self.notadmin.name, model.Action.READ, self.pkg)
        assert not self.authorizer.is_authorized(self.notadmin.name, model.Action.READ, self.private_pkg)
        
        q = self.authorizer.authorized_query(self.notadmin.name, model.Package)
        pkgs = set([pkg.name for pkg in q.all()])
        expected_pkgs = set([u'testpkg', u'testpkg2', u'annakarenina', u'warandpeace'])
        assert_equal(pkgs, expected_pkgs)

    def _assert_relationships(self, rels, expected_rels):
        rels = set([repr(rel) for rel in rels])
        assert_equal(rels, set(expected_rels))

    def test_package_relationships_as_notadmin(self):
        rels = self.authorizer.authorized_package_relationships( \
            self.notadmin.name, self.pkg, None, action=model.Action.READ)
        self._assert_relationships(rels, ['<*PackageRelationship testpkg depends_on testpkg2>'])

        rels = self.authorizer.authorized_package_relationships( \
            self.notadmin.name, self.pkg, self.pkg2, action=model.Action.READ)
        self._assert_relationships(rels, ['<*PackageRelationship testpkg depends_on testpkg2>'])

    def test_package_relationships_as_sysadmin(self):
        rels = self.authorizer.authorized_package_relationships( \
            self.sysadmin.name, self.pkg, None, action=model.Action.READ)
        self._assert_relationships(rels, ['<*PackageRelationship testpkg depends_on testpkg2>', '<*PackageRelationship testpkg depends_on private_pkg>'])

        rels = self.authorizer.authorized_package_relationships( \
            self.notadmin.name, self.pkg, self.pkg2, action=model.Action.READ)
        self._assert_relationships(rels, ['<*PackageRelationship testpkg depends_on testpkg2>'])

class TestLockedDownAuthorizer(object):

    @classmethod
    def setup_class(self):
        CreateTestData.create()
        q = model.Session.query(model.UserObjectRole).filter(sa.or_(model.UserObjectRole.role==Role.EDITOR,
                                                                    model.UserObjectRole.role==Role.ANON_EDITOR,
                                                                    model.UserObjectRole.role==Role.READER))
        q = q.filter(model.UserObjectRole.user==model.User.by_name(u"visitor"))
        for role in q:
            model.Session.delete(role)
        model.repo.commit_and_remove()
        model.repo.new_revision()        
        model.Session.add(model.Package(name=u'testpkg'))
        model.Session.add(model.Package(name=u'testpkg2'))
        model.Session.add(model.User(name=u'testadmin'))
        # Cannot setup testsysadmin user as it is alreade done in
        # the default test data.
        #model.Session.add(model.User(name=u'testsysadmin'))
        model.Session.add(model.User(name=u'notadmin'))
        model.Session.add(model.Group(name=u'testgroup'))
        model.Session.add(model.Group(name=u'testgroup2'))
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

    authorizer = ckan.authz.Authorizer()

    def test_pkg_create(self):
        action = model.Action.PACKAGE_CREATE
        assert self.authorizer.is_authorized(self.admin.name, action, model.System())
        assert self.authorizer.is_authorized(self.notadmin.name, action, model.System())
        assert not self.authorizer.is_authorized(u'blah', action, model.System())
        assert not self.authorizer.is_authorized(u'visitor', action, model.System())
    
    def test_pkg_edit(self):
        #reproduce a bug 
        action = model.Action.EDIT
        assert self.authorizer.is_authorized(self.notadmin.name, action, model.System())
    
    def test_pkg_admin(self):
        action = model.Action.PURGE
        assert self.authorizer.is_authorized(self.admin.name, action, self.pkg)
        assert not self.authorizer.is_authorized(self.admin.name, action, self.pkg2)
        assert not self.authorizer.is_authorized(u'blah', action, self.pkg)

    def test_grp_sys_admin(self):
        action = model.Action.PURGE
        assert self.authorizer.is_authorized(self.sysadmin.name, action, self.grp)
        assert self.authorizer.is_authorized(self.sysadmin.name, action, self.grp2)
        assert not self.authorizer.is_authorized(u'blah', action, self.grp)


class TestAuthorizationGroups(object):

    @classmethod
    def setup_class(self):
        CreateTestData.create()
        model.repo.new_revision()
        model.Session.add(model.Package(name=u'testpkgag'))
        model.Session.add(model.Group(name=u'testgroupag'))
        model.Session.add(model.User(name=u'ag_member'))
        model.Session.add(model.User(name=u'ag_admin'))
        model.Session.add(model.User(name=u'ag_notmember'))
        model.Session.add(model.AuthorizationGroup(name=u'authz_group'))
        model.repo.commit_and_remove()

        pkg = model.Package.by_name(u'testpkgag')
        grp = model.Group.by_name(u'testgroupag')
        authzgrp = model.AuthorizationGroup.by_name(u'authz_group')
        member = model.User.by_name(u'ag_member')
        admin = model.User.by_name(u'ag_admin')
    
        model.setup_default_user_roles(authzgrp, [admin])
        model.add_authorization_group_to_role(authzgrp, model.Role.ADMIN, pkg)
        model.add_authorization_group_to_role(authzgrp, model.Role.ADMIN, grp)
        model.add_user_to_authorization_group(member, authzgrp, model.Role.EDITOR)
        model.repo.commit_and_remove()

        self.authorizer = ckan.authz.Authorizer()
        self.pkg = model.Package.by_name(u'testpkgag')
        self.grp = model.Group.by_name(u'testgroupag')
        self.member = model.User.by_name(u'ag_member')
        self.admin = model.User.by_name(u'ag_admin')
        self.notmember = model.User.by_name(u'ag_notmember')
        self.authzgrp = model.AuthorizationGroup.by_name(u'authz_group')

    @classmethod
    def teardown_class(self):
        model.Session.remove()
        model.repo.rebuild_db()
        model.Session.remove()

    authorizer = ckan.authz.Authorizer()

    def test_get_authorization_groups(self):
        assert self.authzgrp.id == self.authorizer.get_authorization_groups(self.member.name)[0].id
        assert not self.authorizer.get_authorization_groups(self.notmember.name)

    @uses_example_auth_plugin
    def test_get_groups_with_plugin(self):
        groups = self.authorizer.get_authorization_groups(self.member.name)
        assert len(groups) == 2, len(groups)

    def test_edit_via_grp(self):
        action = model.Action.EDIT
        assert not self.authorizer.is_authorized(self.notmember.name, action, self.pkg)
        assert not self.authorizer.is_authorized(self.notmember.name, action, self.grp)
        assert self.authorizer.is_authorized(self.member.name, action, self.pkg)
        assert self.authorizer.is_authorized(self.member.name, action, self.grp)
        
    def test_add_to_authzgrp(self):
        model.Session.add(model.User(name=u'ag_joiner'))
        model.repo.new_revision()
        model.repo.commit_and_remove()
        user = model.User.by_name(u'ag_joiner')
        assert not model.user_in_authorization_group(user, self.authzgrp), user
        model.add_user_to_authorization_group(user, self.authzgrp, model.Role.ADMIN)
        model.repo.new_revision()
        model.repo.commit_and_remove()
        assert model.user_in_authorization_group(user, self.authzgrp)

    def test_remove_from_authzgrp(self):
        model.Session.add(model.User(name=u'ag_leaver'))
        model.repo.new_revision()
        model.repo.commit_and_remove()
        user = model.User.by_name(u'ag_leaver')
        model.add_user_to_authorization_group(user, self.authzgrp, model.Role.ADMIN)
        model.repo.new_revision()
        model.repo.commit_and_remove()
        assert model.user_in_authorization_group(user, self.authzgrp)
        model.remove_user_from_authorization_group(user, self.authzgrp)
        model.repo.new_revision()
        model.repo.commit_and_remove()
        assert not model.user_in_authorization_group(user, self.authzgrp)

    def test_authzgrp_edit_rights(self):
        assert self.authorizer.is_authorized(self.member.name, model.Action.READ, self.authzgrp)
        assert self.authorizer.is_authorized(self.notmember.name, model.Action.READ, self.authzgrp)
        assert self.authorizer.is_authorized(self.member.name, model.Action.EDIT, self.authzgrp)
        assert not self.authorizer.is_authorized(self.member.name, model.Action.PURGE, self.authzgrp)
        assert self.authorizer.is_authorized(self.admin.name, model.Action.PURGE, self.authzgrp)
        assert not self.authorizer.is_authorized(self.notmember.name, model.Action.EDIT, self.authzgrp)

    def test_authorized_query(self):
        assert not self.authorizer.is_authorized(self.notmember.name, model.Action.READ, self.pkg)
        assert self.authorizer.is_authorized(self.member.name, model.Action.READ, self.pkg)
        
        q = self.authorizer.authorized_query(self.notmember.name, model.Package)
        q = q.filter(model.Package.name==self.pkg.name)
        assert not len(q.all()) 
        
        q = self.authorizer.authorized_query(self.member.name, model.Package)
        q = q.filter(model.Package.name==self.pkg.name)
        assert len(q.all()) == 1

    @uses_example_auth_plugin
    def test_authorized_query_with_plugin(self):
        assert self.authorizer.is_authorized(self.notmember.name, model.Action.READ, self.pkg)
