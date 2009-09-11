from pylons import config

import ckan.model as model
from ckan.tests import *
import ckan.authz as authz

class TestCreation(object):

    @classmethod
    def setup_class(self):
        CreateTestData.create()
        self.authorizer = authz.Authorizer()
        model.Session.remove()

    @classmethod
    def teardown_class(self):
        model.Session.remove()
        model.repo.rebuild_db()
        model.Session.remove()

    def test_0_package_role(self):
        uor = model.UserObjectRole(role=model.Role.ADMIN)
        anna = model.Package.by_name(u'annakarenina')
        pr = model.PackageRole(role=model.Role.ADMIN,
                               package=anna)
        
        model.repo.commit_and_remove()

        pr = model.PackageRole.query.filter_by(role=model.Role.ADMIN)
        assert len(pr.all()) == 1, pr.all()

    def test_1_user_role(self):
        anna = model.Package.by_name(u'annakarenina')
        mradmin = model.User.by_name(u'tester')
        role = model.Role.ADMIN
        model.add_user_to_role(mradmin, role, anna)
        model.repo.commit_and_remove()

        anna = model.Package.by_name(u'annakarenina')
        mradmin = model.User.by_name(u'tester')
        roles = self.authorizer.get_roles(mradmin.name, anna)
        print model.PackageRole.query.filter_by(user=mradmin).all()
        assert role in roles, roles

    def test_2_role_action_basic(self):
        admin_role = model.Role.ADMIN
        action = model.Action.EDIT
        context = model.Package.__class__.__name__
        ra = model.RoleAction(role=admin_role,
                              context=context,
                              action=action,
                              )
        model.repo.commit_and_remove()

        ra = model.RoleAction.query.filter_by(role=admin_role,
                                              context=context,
                                              action=action)
        assert len(ra.all()) == 1, ra.all()

class TestDefaultRoles(object):
    @classmethod
    def setup_class(self):
        model.repo.commit_and_remove()
        #Now done in db init
        #model.setup_default_role_actions()

    
    @classmethod
    def teardown_class(self):
        model.Session.remove()
        model.repo.rebuild_db()
        model.Session.remove()

    def is_allowed(self, role, action):
        action_query = model.RoleAction.query.filter_by(role=role,
                                                        action=action)
        return action_query.count() > 0
        
    def test_read(self):
        assert self.is_allowed(model.Role.READER, model.Action.READ)
        assert self.is_allowed(model.Role.EDITOR, model.Action.READ)

    def test_edit(self):
        assert not self.is_allowed(model.Role.READER, model.Action.EDIT)
        assert self.is_allowed(model.Role.EDITOR, model.Action.EDIT)

    def test_create(self):
        assert self.is_allowed(model.Role.READER, model.Action.CREATE)
        assert self.is_allowed(model.Role.EDITOR, model.Action.CREATE)

    def test_edit_permissions(self):
        assert not self.is_allowed(model.Role.READER, model.Action.EDIT_PERMISSIONS)
        assert not self.is_allowed(model.Role.EDITOR, model.Action.EDIT_PERMISSIONS)

    def test_delete(self):
        assert not self.is_allowed(model.Role.READER, model.Action.DELETE)
        assert not self.is_allowed(model.Role.EDITOR, model.Action.DELETE)

    def test_purge(self):
        assert not self.is_allowed(model.Role.READER, model.Action.PURGE)
        assert not self.is_allowed(model.Role.EDITOR, model.Action.PURGE)

class TestDefaultPackageUserRoles(object):
    @classmethod
    def setup_class(self):
        CreateTestData.create()
        model.repo.new_revision()
        self.authorizer = authz.Authorizer()
        pkg = model.Package(name=u'testpkg')
        joeadmin = model.User.by_name(u'joeadmin')
        assert joeadmin
        model.setup_default_user_roles(pkg, [joeadmin])
        model.repo.commit_and_remove()

        self.pkg = model.Package.by_name(u'testpkg')
        self.joeadmin = model.User.by_name(u'joeadmin')
        self.logged_in = model.User.by_name(model.PSEUDO_USER__LOGGED_IN)
        self.visitor = model.User.by_name(model.PSEUDO_USER__VISITOR)

    @classmethod
    def teardown_class(self):
        model.Session.remove()
        model.repo.rebuild_db()
        model.Session.remove()

    def test_admin(self):
        roles = self.authorizer.get_roles(self.joeadmin.name, self.pkg)
        assert model.Role.ADMIN in roles, self.authorizer.get_package_roles(self.pkg)

    def test_logged_in(self):
        roles = self.authorizer.get_roles(self.logged_in.name, self.pkg)
        assert model.Role.EDITOR in roles, roles
        assert model.Role.READER in roles, roles

    def test_visitor(self):
        roles = self.authorizer.get_roles(self.visitor.name, self.pkg)
        assert model.Role.EDITOR in roles, roles
        assert model.Role.READER in roles, roles


class TestUsage(object):

    @classmethod
    def setup_class(self):
        CreateTestData.create()
        model.Session.remove()
        self.authorizer = authz.Authorizer()

        self.admin_role = model.Role.ADMIN
        self.editor_role = model.Role.EDITOR
        self.reader_role = model.Role.READER

        anna = model.Package.by_name(u'annakarenina')
        tester = model.User.by_name(u'tester')
        model.add_user_to_role(tester, self.admin_role, anna)

        self.context = model.Package.__class__.__name__
        ra = model.RoleAction(role=self.admin_role,
                              context=self.context,
                              action=model.Action.EDIT,
                              )
        ra = model.RoleAction(role=self.editor_role,
                              context=self.context,
                              action=model.Action.EDIT,
                              )
        ra = model.RoleAction(role=self.reader_role,
                              context=self.context,
                              action=model.Action.READ,
                              )
        anna = model.Package.by_name(u'annakarenina')
        mradmin = model.User(name=u'mradmin')
        mreditor = model.User(name=u'mreditor')
        mrreader = model.User(name=u'mrreader')
        model.repo.commit_and_remove()

        mradmin = model.User.by_name(u'mradmin')
        mreditor = model.User.by_name(u'mreditor')
        mrreader = model.User.by_name(u'mrreader')
        model.add_user_to_role(mradmin, self.admin_role, anna)
        model.add_user_to_role(mreditor, self.editor_role, anna)
        model.add_user_to_role(mrreader, self.reader_role, anna)
        model.repo.commit_and_remove()

        self.mradmin = model.User.by_name(u'mradmin')
        self.mreditor = model.User.by_name(u'mreditor')
        self.mrreader = model.User.by_name(u'mrreader')
        self.war = model.Package.by_name(u'warandpeace')
        self.anna = model.Package.by_name(u'annakarenina')


    @classmethod
    def teardown_class(self):
        model.Session.remove()
        model.repo.rebuild_db()
        model.Session.remove()

    def test_1_user_role(self):
        anna = model.Package.by_name(u'annakarenina')
        tester = model.User.by_name(u'tester')
        roles = self.authorizer.get_roles(tester.name, anna)
        print model.PackageRole.query.filter_by(user=tester).all()
        assert self.admin_role in roles, roles

    def test_2_is_auth_admin(self):
        ra = model.RoleAction.query.filter_by(role=self.admin_role,
                                              context=self.context,
                                              action=model.Action.EDIT)
        assert len(ra.all()) == 1, ra.all()

        assert self.authorizer.get_roles(self.mradmin.name, self.anna)
        
        assert self.authorizer.is_authorized(username=self.mradmin.name,
                                             action=model.Action.EDIT,
                                             domain_object=self.anna)

    def test_2_is_auth_editor_edit(self):
        war = model.Package.by_name(u'warandpeace')
        assert self.authorizer.is_authorized(username=self.mreditor.name,
                                             action=model.Action.EDIT,
                                             domain_object=self.anna)

    def test_2_is_auth_reader_edit(self):
        assert not self.authorizer.is_authorized(username=self.mrreader.name,
                                                 action=model.Action.EDIT,
                                                 domain_object=self.anna)
    def test_2_is_auth_reader_read(self):
        assert self.authorizer.is_authorized(username=self.mrreader.name,
                                             action=model.Action.READ,
                                             domain_object=self.anna)

class TestUseCasePermissions:
    @classmethod
    def setup_class(self):
        CreateTestData.create()
        model.Session.remove()
        self.authorizer = authz.Authorizer()

        self.admin_role = model.Role.ADMIN
        self.editor_role = model.Role.EDITOR
        self.reader_role = model.Role.READER

        john = model.User(name=u'john')
        
        # setup annakarenina with default roles
        anna = model.Package.by_name(u'annakarenina')
        model.clear_user_roles(anna)
        annakarenina_creator = model.User(name=u'annakarenina_creator')
        model.setup_default_user_roles(anna, [annakarenina_creator])

        # setup warandpeace with no roles
        war = model.Package.by_name(u'warandpeace')
        model.clear_user_roles(war)

        # setup restricted package - visitors can't change
        restricted = model.Package(name=u'restricted')
        vrestricted = model.Package(name=u'vrestricted')
        mreditor = model.User(name=u'mreditor')
        mrreader = model.User(name=u'mrreader')
        model.repo.new_revision()
        model.repo.commit_and_remove()
        visitor_roles = []
        logged_in_roles = [model.Role.EDITOR, model.Role.READER]
        logged_in_roles_v = []
        restricted = model.Package.by_name(u'restricted')
        vrestricted = model.Package.by_name(u'vrestricted')
        model.setup_user_roles(restricted, visitor_roles, logged_in_roles)
        model.setup_user_roles(vrestricted, visitor_roles, logged_in_roles_v)
        model.repo.commit_and_remove()
        mreditor = model.User.by_name(u'mreditor')
        model.add_user_to_role(mreditor, model.Role.EDITOR, restricted)

        self.mreditor = model.User.by_name(u'mreditor')
        self.mrreader = model.User.by_name(u'mrreader')
        self.annakarenina_creator = model.User.by_name(u'annakarenina_creator')
        self.logged_in = model.User.by_name(model.PSEUDO_USER__LOGGED_IN)
        self.visitor = model.User.by_name(model.PSEUDO_USER__VISITOR)
        self.john = model.User.by_name(u'john')
        self.war = model.Package.by_name(u'warandpeace')
        self.anna = model.Package.by_name(u'annakarenina')
        self.restricted = model.Package.by_name(u'restricted')
        self.vrestricted = model.Package.by_name(u'vrestricted')


    @classmethod
    def teardown_class(self):
        model.Session.remove()
        model.repo.rebuild_db()
        model.Session.remove()

    def test_01_visitor_reads(self):
        assert self.authorizer.is_authorized(username=self.visitor.name,
                                             action=model.Action.READ,
                                             domain_object=self.anna)

    def test_02_visitor_edits(self):
        assert self.authorizer.is_authorized(username=self.visitor.name,
                                             action=model.Action.EDIT,
                                             domain_object=self.anna)

    def test_03_logged_in_reads(self):
        assert self.authorizer.is_authorized(username=self.logged_in.name,
                                             action=model.Action.READ,
                                             domain_object=self.anna)

    def test_04a_logged_in_edits(self):
        assert self.authorizer.is_authorized(username=self.logged_in.name,
                                             action=model.Action.EDIT,
                                             domain_object=self.anna)

    def test_04b_anyone_logged_in_edits(self):
        assert self.authorizer.is_authorized(username=self.john.name,
                                             action=model.Action.EDIT,
                                             domain_object=self.restricted)

    def test_05_user_creates_package(self):
        assert self.authorizer.is_authorized(username=self.annakarenina_creator.name,
                                             action=model.Action.DELETE,
                                             domain_object=self.anna)
        creator_roles = self.authorizer.get_roles(self.annakarenina_creator.name, self.anna)
        assert model.Role.ADMIN in creator_roles, creator_roles

    def test_05b_visitor_creates_package(self):
        try:
            model.setup_default_user_roles(self.anna, [self.visitor])
        except model.NotRealUserException, e:
            pass
        else:
            assert 0, 'Visitor should not be allowed to be admin on a package'

    def test_06_to_09_package_admin_adds_admin(self):
        assert self.authorizer.is_authorized(username=self.annakarenina_creator.name,
                                             action=model.Action.EDIT_PERMISSIONS,
                                             domain_object=self.anna)

    def test_10_visitor_role(self):
        assert not self.authorizer.is_authorized(username=self.visitor.name,
                                             action=model.Action.EDIT,
                                             domain_object=self.war)
        model.add_user_to_role(self.visitor, model.Role.EDITOR, self.war)
        assert self.authorizer.is_authorized(username=self.visitor.name,
                                             action=model.Action.EDIT,
                                             domain_object=self.war)

    def test_11_sysadmin_change_permissions(self):
        sysadmin = u'testsysadmin' # from test.ini
        admins = config.get('auth.admins', '').split()
        assert sysadmin in admins

        assert self.authorizer.is_authorized(username=sysadmin,
                                             action=model.Action.EDIT_PERMISSIONS,
                                             domain_object=self.anna)

    def test_12_visitor_changes_restricted_package(self):
        assert not self.authorizer.is_authorized(username=self.visitor.name,
                                                 action=model.Action.EDIT,
                                                 domain_object=self.restricted), self.authorizer._package_role_table(self.restricted)

    def test_13_user_changes_vrestricted_package(self):
        assert not self.authorizer.is_authorized(username=self.john.name,
                                                 action=model.Action.EDIT,
                                                 domain_object=self.vrestricted), self.authorizer._package_role_table(self.vrestricted)

    def test_14_visitor_reads_restricted_package(self):
        assert not self.authorizer.is_authorized(username=self.visitor.name,
                                                 action=model.Action.READ,
                                                 domain_object=self.restricted), self.authorizer._package_role_table(self.restricted)

    def test_15_user_reads_vrestricted_package(self):
        assert not self.authorizer.is_authorized(username=self.john.name,
                                                 action=model.Action.READ,
                                                 domain_object=self.vrestricted), self.authorizer._package_role_table(self.vrestricted)

    def _test_in_a_perfect_world(self):
        # this doesn't work because of many:many relationship problems
        anna = model.Package.by_name('annakarenina')
        mradmin = model.User(name='mradmin')
        role = model.Role.ADMIN
        anna.roles[role] = [mradmin]
        model.repo.commit_and_remove()
        anna = model.Package.by_name('annakarenina')
        print model.PackageRole.query.all()
        assert mradmin in anna.roles[role], anna.roles
        

