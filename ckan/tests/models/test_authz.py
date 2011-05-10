from pylons import config

import ckan.model as model
from ckan.tests import *
import ckan.authz as authz

class TestCreation(object):

    @classmethod
    def setup_class(self):
        model.Session.remove()
        model.repo.init_db()
        model.repo.new_revision()
        p1 = model.Package(name=u'annakarenina')
        p2 = model.Package(name=u'warandpeace')
        p3 = model.Package(name=u'test0')
        mradmin = model.User(name=u'tester')
        for obj in (p1, p2, p3, mradmin):
            model.Session.add(obj)
        self.authorizer = authz.Authorizer()
        model.repo.commit_and_remove()

    @classmethod
    def teardown_class(self):
        model.Session.remove()
        model.repo.rebuild_db()
        model.Session.remove()

    def test_0_package_role(self):
        test0 = model.Package.by_name(u'test0')
        mradmin = model.User.by_name(u'tester')
        uor = model.UserObjectRole(role=model.Role.ADMIN, user=mradmin)
        model.Session.add(uor)
        pr = model.PackageRole(role=model.Role.ADMIN,
                               package=test0,
                               user=mradmin
                               )
        model.Session.add(pr)
        test0 = model.Package.by_name(u'test0')        
        prs = model.Session.query(model.PackageRole).filter_by(
            role=model.Role.ADMIN,
            package=test0, user=mradmin)
        model.repo.commit_and_remove()

        # basic test of existence
        assert len(prs.all()) == 1, prs.all()
        pr = prs.first()
        assert pr.context == 'Package', pr.context

        # test delete-orphan
        q = model.Session.query(model.UserObjectRole)
        q = q.filter_by(user=mradmin)
        assert q.count() == 2, q.all()
        uow = q.filter_by(context=u'user_object').first()
        uow.user = None
        model.repo.commit_and_remove()
        assert q.count() == 1, q.all()

        # now test delete-orphan on PackageRole
        prs = model.Session.query(model.PackageRole)
        pr = prs.first()
        pr.user = None
        model.repo.commit_and_remove()
        prs = model.Session.query(model.PackageRole)
        # This fails!!
        # It seems that delete-orphan does not work for inheriting object!!
        # assert len(prs.all()) == 0, prs.all()

    def test_1_user_role(self):
        anna = model.Package.by_name(u'annakarenina')
        mradmin = model.User.by_name(u'tester')
        role = model.Role.ADMIN
        model.add_user_to_role(mradmin, role, anna)
        model.repo.commit_and_remove()

        anna = model.Package.by_name(u'annakarenina')
        mradmin = model.User.by_name(u'tester')
        roles = self.authorizer.get_roles(mradmin.name, anna)
        assert role in roles, roles

    def test_2_role_action_basic(self):
        admin_role = model.Role.ADMIN
        action = model.Action.EDIT
        context = unicode(model.Package.__name__)
        ra = model.RoleAction(role=admin_role,
                              context=context,
                              action=action,
                              )
        model.Session.add(ra)
        model.repo.commit_and_remove()

        ra = model.Session.query(model.RoleAction).filter_by(role=admin_role,
                                              context=context,
                                              action=action)
        assert len(ra.all()) == 1, ra.all()

    def test_3_group_role(self):
        war = model.Group.by_name(u'warandpeace')
        mradmin = model.User.by_name(u'tester')
        pr = model.GroupRole(role=model.Role.ADMIN,
                               group=war,
                               user=mradmin)
        model.Session.add(pr)
        model.repo.commit_and_remove()

        pr = model.Session.query(model.GroupRole).filter_by(role=model.Role.ADMIN,
                                               group=war)
                                               
        assert len(pr.all()) == 1, pr.all()


class TestDefaultRoles(object):
    @classmethod
    def setup_class(self):
        model.Session.remove()
        CreateTestData.create()
        model.Session.remove()

    @classmethod
    def teardown_class(self):
        model.Session.remove()
        model.repo.rebuild_db()
        model.Session.remove()
        
    def is_allowed(self, role, action):
        action_query = model.Session.query(model.RoleAction).filter_by(role=role,
                                                        action=action)
        return action_query.count() > 0
        
    def test_read(self):
        assert self.is_allowed(model.Role.READER, model.Action.READ)
        assert self.is_allowed(model.Role.ANON_EDITOR, model.Action.READ)
        assert self.is_allowed(model.Role.EDITOR, model.Action.READ)

    def test_edit(self):
        assert not self.is_allowed(model.Role.READER, model.Action.EDIT)
        assert self.is_allowed(model.Role.ANON_EDITOR, model.Action.EDIT)
        assert self.is_allowed(model.Role.EDITOR, model.Action.EDIT)

    def test_create(self):
        assert not self.is_allowed(model.Role.READER, model.Action.PACKAGE_CREATE)
        assert self.is_allowed(model.Role.ANON_EDITOR, model.Action.PACKAGE_CREATE)
        assert self.is_allowed(model.Role.EDITOR, model.Action.PACKAGE_CREATE)

        assert not self.is_allowed(model.Role.READER, model.Action.GROUP_CREATE)
        assert not self.is_allowed(model.Role.ANON_EDITOR, model.Action.GROUP_CREATE)
        assert self.is_allowed(model.Role.EDITOR, model.Action.GROUP_CREATE)

    def test_edit_permissions(self):
        assert not self.is_allowed(model.Role.READER, model.Action.EDIT_PERMISSIONS)
        assert not self.is_allowed(model.Role.EDITOR, model.Action.EDIT_PERMISSIONS)

    def test_change_state(self):
        assert not self.is_allowed(model.Role.READER, model.Action.CHANGE_STATE)
        assert not self.is_allowed(model.Role.ANON_EDITOR, model.Action.CHANGE_STATE)
        assert not self.is_allowed(model.Role.EDITOR, model.Action.CHANGE_STATE)

    def test_purge(self):
        assert not self.is_allowed(model.Role.READER, model.Action.PURGE)
        assert not self.is_allowed(model.Role.ANON_EDITOR, model.Action.PURGE)
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
        assert model.Role.ADMIN in roles, self.authorizer.get_domain_object_roles_printable(self.pkg)

    def test_logged_in(self):
        roles = self.authorizer.get_roles(self.logged_in.name, self.pkg)
        assert model.Role.EDITOR in roles, roles

    def test_visitor(self):
        roles = self.authorizer.get_roles(self.visitor.name, self.pkg)
        assert model.Role.EDITOR in roles, roles


class TestUsage(object):

    @classmethod
    def setup_class(self):
        model.repo.init_db()
        self.authorizer = authz.Authorizer()

        self.admin_role = model.Role.ADMIN
        self.editor_role = model.Role.EDITOR
        self.reader_role = model.Role.READER

        model.repo.new_revision()
        anna = model.Package(name=u'annakarenina')
        war = model.Package(name=u'warandpeace')
        mradmin = model.User(name=u'mradmin')
        mreditor = model.User(name=u'mreditor')
        mrreader = model.User(name=u'mrreader')
        tester = model.User(name=u'tester')
        anauthzgroup = model.AuthorizationGroup(name=u'anauthzgroup')
        for obj in [anna, war, mradmin, mreditor, mrreader, tester, anauthzgroup]:
            model.Session.add(obj)
        model.repo.commit_and_remove()

        anna = model.Package.by_name(u'annakarenina')
        tester = model.User.by_name(u'tester')
        model.add_user_to_role(tester, self.admin_role, anna)

        self.context = unicode(model.Package.__name__)
        ra1 = model.RoleAction(role=self.admin_role,
                              context=self.context,
                              action=model.Action.EDIT,
                              )
        ra2 = model.RoleAction(role=self.editor_role,
                              context=self.context,
                              action=model.Action.EDIT,
                              )
        ra3 = model.RoleAction(role=self.reader_role,
                              context=self.context,
                              action=model.Action.READ,
                              )
        for obj in [ra1, ra2, ra3]:
            model.Session.add(obj)
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
        assert self.admin_role in roles, roles

    def test_2_is_auth_admin(self):
        ra = model.Session.query(model.RoleAction).filter_by(role=self.admin_role,
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

    def test_3_add_twice_remove_twice(self):
        tester = model.User.by_name(u'tester')
        war = model.Package.by_name(u'warandpeace')

        def tester_roles():
            return [x.role \
             for x in model.Session.query(model.PackageRole).all() \
             if x.user and x.user.name=='tester' and x.package.name==u'warandpeace']
          
        assert len(tester_roles()) == 0, "wrong number of roles for tester"
        model.add_user_to_role(tester, model.Role.ADMIN, war)
        model.repo.commit_and_remove()
        assert len(tester_roles()) == 1, "wrong number of roles for tester"
        model.add_user_to_role(tester, model.Role.ADMIN, war)
        model.repo.commit_and_remove()

        assert len(tester_roles()) == 1, "wrong number of roles for tester"
        model.remove_user_from_role(tester, model.Role.ADMIN, war)
        assert len(tester_roles()) == 0, "wrong number of roles for tester"
        model.remove_user_from_role(tester, model.Role.ADMIN, war)
        assert len(tester_roles()) == 0, "wrong number of roles for tester"

    def test_4_add_twice_remove_twice_for_authzgroups(self):
        aag = model.AuthorizationGroup.by_name(u'anauthzgroup')
        war = model.Package.by_name(u'warandpeace')

        def aag_roles():
            return [x.role \
             for x in model.Session.query(model.PackageRole).all() \
             if x.authorized_group and x.authorized_group.name=='anauthzgroup' and x.package.name==u'warandpeace']
          
        assert len(aag_roles()) == 0, "wrong number of roles for anauthzgroup"
        model.add_authorization_group_to_role(aag, model.Role.ADMIN, war)
        model.repo.commit_and_remove()
        assert len(aag_roles()) == 1, "wrong number of roles for anauthzgroup"
        model.add_authorization_group_to_role(aag, model.Role.ADMIN, war)
        model.repo.commit_and_remove()

        assert len(aag_roles()) == 1, "wrong number of roles for anauthzgroup"
        model.remove_authorization_group_from_role(aag, model.Role.ADMIN, war)
        assert len(aag_roles()) == 0, "wrong number of roles for anauthzgroup"
        model.remove_authorization_group_from_role(aag, model.Role.ADMIN, war)
        assert len(aag_roles()) == 0, "wrong number of roles for anauthzgroup"




class TestMigrate:
    @classmethod
    def setup_class(self):
        model.Session.remove()
        model.repo.init_db()
        model.repo.commit_and_remove()
        model.Session.remove()

    @classmethod
    def teardown_class(self):
        model.Session.remove()
        model.repo.rebuild_db()
        model.Session.remove()

    def test_give_default_permissions(self):
        model.repo.new_revision()
        anna = model.Package(name=u'annakarenina')
        war = model.Package(name=u'warandpeace')
        warauthor1 = model.User(name=u'warauthor1')
        warauthor2 = model.User(name=u'warauthor2')
        for obj in [anna, war, warauthor1, warauthor2]:
            model.Session.add(obj)
        model.repo.commit_and_remove()

        # make changes
        anna = model.Package.by_name(u'annakarenina')
        rev = model.repo.new_revision() 
        rev.author = u'warauthor1'
        anna.title = u'title1'
        model.repo.commit_and_remove()

        anna = model.Package.by_name(u'annakarenina')
        rev = model.repo.new_revision() 
        rev.author = u'warauthor2'
        anna.title = u'title2'
        model.repo.commit_and_remove()

        model.give_all_packages_default_user_roles()
        model.Session.commit()

        anna = model.Package.by_name(u'annakarenina')
        war = model.Package.by_name(u'warandpeace')
        warauthor1 = model.User.by_name(u'warauthor1')
        warauthor2 = model.User.by_name(u'warauthor2')
        visitor = model.User.by_name(model.PSEUDO_USER__VISITOR)
        assert model.user_has_role(visitor, model.Role.EDITOR, anna)
        assert model.user_has_role(visitor, model.Role.EDITOR, war)
        assert not model.user_has_role(warauthor1, model.Role.ADMIN, war)
        assert model.user_has_role(warauthor1, model.Role.ADMIN, anna)
        assert model.user_has_role(warauthor2, model.Role.ADMIN, anna)

class TestUseCasePermissions:
    @classmethod
    def setup_class(self):
        model.Session.remove()
        CreateTestData.create()
        model.Session.remove()
        self.authorizer = authz.Authorizer()

        self.admin_role = model.Role.ADMIN
        self.editor_role = model.Role.EDITOR
        self.reader_role = model.Role.READER

        john = model.User(name=u'john')
        model.Session.add(john)
        
        # setup annakarenina with default roles
        anna = model.Package.by_name(u'annakarenina')
        model.clear_user_roles(anna)
        annakarenina_creator = model.User(name=u'annakarenina_creator')
        model.Session.add(annakarenina_creator)
        model.repo.commit_and_remove()
        model.setup_default_user_roles(anna, [annakarenina_creator])
        model.repo.commit_and_remove()

        # setup warandpeace with no roles
        war = model.Package.by_name(u'warandpeace')
        model.clear_user_roles(war)

        # setup restricted package - visitors can't change
        restricted = model.Package(name=u'restricted')
        vrestricted = model.Package(name=u'vrestricted')
        mreditor = model.User(name=u'mreditor')
        mrreader = model.User(name=u'mrreader')
        self.mrsysadmin = u'mrsysadmin'
        mrsysadmin = model.User(name=self.mrsysadmin)
        model.repo.new_revision()
        model.Session.add_all([restricted,
            vrestricted,mreditor,mrreader,mrsysadmin])
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

        mrsysadmin = model.User.by_name(u'mrsysadmin')
        model.add_user_to_role(mrsysadmin, model.Role.ADMIN, model.System())
        model.repo.commit_and_remove()

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
                                             action=model.Action.CHANGE_STATE,
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
                action=model.Action.EDIT, domain_object=self.war)

        self.visitor = model.User.by_name(model.PSEUDO_USER__VISITOR)
        self.war = model.Package.by_name(u'warandpeace')
        model.add_user_to_role(self.visitor, model.Role.EDITOR, self.war)
        model.repo.commit_and_remove()
        assert self.authorizer.is_authorized(username=self.visitor.name,
                action=model.Action.EDIT, domain_object=self.war)

    def test_11_sysadmin_change_permissions(self):
        assert self.authorizer.is_authorized(username=self.mrsysadmin,
                action=model.Action.EDIT_PERMISSIONS, domain_object=self.anna)

    def test_12_visitor_changes_restricted_package(self):
        assert not self.authorizer.is_authorized(username=self.visitor.name,
                                                 action=model.Action.EDIT,
                                                 domain_object=self.restricted), self.authorizer.get_domain_object_roles_printable(self.restricted)

    def test_13_user_changes_vrestricted_package(self):
        assert not self.authorizer.is_authorized(username=self.john.name,
                                                 action=model.Action.EDIT,
                                                 domain_object=self.vrestricted), self.authorizer.get_domain_object_roles_printable(self.vrestricted)

    def test_14_visitor_reads_restricted_package(self):
        assert not self.authorizer.is_authorized(username=self.visitor.name,
                                                 action=model.Action.READ,
                                                 domain_object=self.restricted), self.authorizer.get_domain_object_roles_printable(self.restricted)

    def test_15_user_reads_vrestricted_package(self):
        assert not self.authorizer.is_authorized(username=self.john.name,
                                                 action=model.Action.READ,
                                                 domain_object=self.vrestricted), self.authorizer.get_domain_object_roles_printable(self.vrestricted)

        

