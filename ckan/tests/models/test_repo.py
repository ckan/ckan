from nose.plugins.skip import SkipTest

from ckan import model
from ckan.authz import Authorizer
from ckan.tests import is_migration_supported

const_user_names = [u'logged_in', u'visitor']
const_role_actions = [
    '<RoleAction role="editor" action="edit" context="">',
    '<RoleAction role="editor" action="create-package" context="">',
    '<RoleAction role="editor" action="create-group" context="">',
    '<RoleAction role="editor" action="create-authorization-group" context="">',
    '<RoleAction role="editor" action="read" context="">',
    '<RoleAction role="editor" action="read-site" context="">',
    '<RoleAction role="editor" action="read-user" context="">',
    '<RoleAction role="editor" action="create-user" context="">',
    '<RoleAction role="editor" action="file-upload" context="">',    
    '<RoleAction role="anon_editor" action="edit" context="">',
    '<RoleAction role="anon_editor" action="create-package" context="">',
    '<RoleAction role="anon_editor" action="read" context="">',
    '<RoleAction role="anon_editor" action="read-site" context="">',
    '<RoleAction role="anon_editor" action="read-user" context="">',
    '<RoleAction role="anon_editor" action="create-user" context="">',
    '<RoleAction role="anon_editor" action="file-upload" context="">',    
    '<RoleAction role="reader" action="read" context="">',
    '<RoleAction role="reader" action="read-site" context="">',
    '<RoleAction role="reader" action="read-user" context="">',
    '<RoleAction role="reader" action="create-user" context="">',
]

class InitialStateTestCase(object):
    # tests for the state of ckan model when it is installed out of the box

    def test_pseudo_users(self):
        users = model.Session.query(model.User).all()
        users_names = [user.name for user in users]
        const_user_names = [u'logged_in', u'visitor']
        user_differences = set(users_names) ^ set(const_user_names)
        assert not user_differences, 'Expected %r but got %r' % \
               (const_user_names, users_names)

    def test_system_edit_authorized(self):
        authorizer = Authorizer()
        auth_for_create = authorizer.is_authorized(\
            u'johndoe', model.Action.PACKAGE_CREATE, model.System())
        assert auth_for_create

    def test_default_system_user_roles(self):
        uors = model.Session.query(model.UserObjectRole).all()
        uors_str = [repr(uor) for uor in uors]
        expected_uors_str = [
            '<SystemRole user="visitor" role="anon_editor" context="System">',
            '<SystemRole user="logged_in" role="editor" context="System">',
            ]
        uor_differences = set(uors_str) ^ set(expected_uors_str)
        assert not uor_differences, 'Expected %r but got %r' % \
               (expected_uors_str, uors_str)

    def test_role_actions(self):
        ras = model.Session.query(model.RoleAction).all()
        ras_str = [repr(ra) for ra in ras]
        ra_differences = set(ras_str) ^ set(const_role_actions)
        assert not ra_differences, 'Expected %r but got %r' % \
               (const_role_actions, ras_str)


class DbFromModelTestCase(object):
    @classmethod
    def setup_class(cls):
        model.repo.clean_db()
        model.repo.init_db()

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()

class DbFromMigrationTestCase(object):
    
    @classmethod
    def setup_class(cls):
        if not is_migration_supported():
            raise SkipTest('Search not supported')
        model.repo.clean_db()
        model.repo.upgrade_db()
        model.repo.init_db()

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()


class TestInitialStateFromModel(InitialStateTestCase, DbFromModelTestCase):
    pass

class TestInitialStateFromMigration(InitialStateTestCase, DbFromMigrationTestCase):
    pass


class TestUpgrade(object):
    @classmethod
    def setup_class(cls):
        if not is_migration_supported():
            raise SkipTest('Search not supported')

        # delete all objects manually
        rev = model.repo.new_revision() 
        users = model.Session.query(model.User).all()
        uors = model.Session.query(model.UserObjectRole).all()
        ras = model.Session.query(model.RoleAction).all()
        for obj in users + uors + ras:
            obj.delete()
        model.repo.commit_and_remove()

        # db will already be on the latest version so
        # this should only reinstate the constant objects
        model.repo.init_const_data()
        
    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()

    def test_user_consts(self):
        users = model.Session.query(model.User).all()
        users_names = [user.name for user in users]        
        user_differences = set(users_names) ^ set(const_user_names)
        assert not user_differences, 'Expected %r but got %r' % \
               (const_user_names, users_names)

    def test_user_object_roles_not_recreated(self):
        # all user object roles are configured, therefore upgrading
        # the db should not recreate them.
        uors = model.Session.query(model.UserObjectRole).all()
        assert not uors, uors

    def test_role_action_consts(self):
        ras = model.Session.query(model.RoleAction).all()
        ras_str = [repr(ra) for ra in ras]
        ra_differences = set(ras_str) ^ set(const_role_actions)
        assert not ra_differences, 'Expected %r but got %r' % \
               (const_role_actions, ras_str)
