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

    ##TODO
    ##6. An admin of a package adds a user as an admin

    ##TODO
    ##7. An admin of a package removes a user as an admin

    ##TODO
    ##8. Ditto for admin re. editor

    ##TODO
    ##9. Ditto for admin re. reader

    ##TODO
    ##10. We wish to be able assign roles to 2 specific entire groups in addition to specific users: 'visitor', 'users'. These will be termed pseudo-users as we do not have AC 'groups' as such.

    ##TODO
    ##11. The sysadmin alters the assignment of entities to roles for any package
