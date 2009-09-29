import simplejson

import ckan.model as model
from ckan.tests import *
from ckan.lib.base import *
import ckan.authz as authz

class TestUsage(TestController):
    deleted = model.State.query.filter_by(name='deleted').one()
    active = model.State.query.filter_by(name='active').one()
    
    @classmethod
    def _create_test_data(self):
        self.modes = ('--', 'r-', 'w-', 'rr', 'wr', 'ww', 'deleted') #  logged-in, visitor
        for mode in self.modes:
            model.Package(name=unicode(mode))
        model.User(name=u'testsysadmin') # in test.ini
        model.User(name=u'admin')
        model.User(name=u'editor')
        model.User(name=u'reader')
        model.User(name=u'mrloggedin')
        model.User(name=u'adminfriend')
        model.Group(name=u'testgroup')
        visitor_name = '123.12.12.123'
        rev = model.repo.new_revision()
        model.repo.commit_and_remove()

        testsysadmin = model.User.by_name(u'testsysadmin')
        admin = model.User.by_name(u'admin')
        editor = model.User.by_name(u'editor')
        reader = model.User.by_name(u'reader')
        mrloggedin = model.User.by_name(name=u'mrloggedin')
        visitor = model.User.by_name(name=model.PSEUDO_USER__VISITOR)
        group = model.Group.by_name(u'testgroup')
        for mode in self.modes:
            pkg = model.Package.by_name(unicode(mode))
            group.packages.append(pkg)
            model.add_user_to_role(admin, model.Role.ADMIN, pkg)
            model.add_user_to_role(editor, model.Role.EDITOR, pkg)
            model.add_user_to_role(reader, model.Role.READER, pkg)
            if mode == u'deleted':
                pkg.state = model.State.query.filter_by(name='deleted').one()
            else:
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
        if action in (model.Action.EDIT, model.Action.READ):
            offset = url_for(controller='package', action=action, id=unicode(mode))
        elif action == 'search':
            offset = '/package/search?q=%s' % unicode(mode)
        elif action == 'list':
            offset = '/package/list'
        else:
            raise NotImplementedError            
        res = self.app.get(offset, extra_environ={'REMOTE_USER': user.name.encode('utf8')}, expect_errors=True)
        return mode in res and u'error' not in res and res.status==200 and not '0 packages found' in res

    def _do_test_rest(self, action, user, mode):
        # Test action on REST
        if action == model.Action.EDIT:
            offset = '/api/rest/package/%s' % unicode(mode)
            postparams = '%s=1' % simplejson.dumps({'title':u'newtitle'})
            func = self.app.post
        elif action == model.Action.READ:
            offset = '/api/rest/package/%s' % unicode(mode)
            postparams = None
            func = self.app.get
        elif action == 'search':
            offset = '/api/search/package?q=%s' % unicode(mode)
            postparams = None
            func = self.app.get
        else:
            raise NotImplementedError
        res = func(offset, params=postparams,
                   extra_environ={'Authorization' : str(user.apikey)},
                   expect_errors=True)
        return mode in res and u'error' not in res and res.status==200 and u'0 packages found' not in res
        
    def _test_can(self, action, user, modes, test=['wui', 'rest']):
        for i, mode in enumerate(modes):
            if 'wui' in test:
                ok_wui = self._do_test_wui(action, user, mode)
                assert ok_wui, '(%i) Should be able to %r %r as user %r (WUI interface)' % (i, action, mode, user.name)
            if 'rest' in test:
                ok_rest = self._do_test_rest(action, user, mode)
                assert ok_rest, '(%i) Should be able to %r %r as user %r (REST interface)' % (i, action, mode, user.name)

    def _test_cant(self, action, user, modes, test=['wui', 'rest']):
        for i, mode in enumerate(modes):
            if 'wui' in test:
                ok_wui = self._do_test_wui(action, user, mode)
                assert not ok_wui, '(%i) Should NOT be able to %r %r as user %r (WUI interface)' % (i, action, mode, user.name)
            if 'rest' in test:
                ok_rest = self._do_test_rest(action, user, mode)
                assert not ok_rest, '(%i) Should NOT be able to %r %r as user %r (REST interface)' % (i, action, mode, user.name)

    # Tests numbered by the use case

    def test_14_visitor_reads_stopped(self): 
        self._test_cant('read', self.visitor, ['--', 'r-', 'w-'])
    def test_01_visitor_reads(self): 
        self._test_can('read', self.visitor, ['rr', 'wr', 'ww'])

    def test_12_visitor_edits_stopped(self):
        self._test_cant('edit', self.visitor, ['ww'], test=['rest'])
        self._test_cant('edit', self.visitor, ['--', 'r-', 'w-', 'rr', 'wr'], test=['wui'])
        self._test_cant('edit', self.visitor, ['--', 'r-', 'w-', 'rr', 'wr', 'ww'], test=['rest'])
    def test_02_visitor_edits(self):
        self._test_can('edit', self.visitor, ['ww'], test=['wui'])
        self._test_can('edit', self.visitor, [], test=['rest'])

    def test_15_user_reads_stopped(self):
        self._test_cant('read', self.mrloggedin, ['--'])
    def test_03_user_reads(self):
        self._test_can('read', self.mrloggedin, ['r-', 'w-', 'rr', 'wr', 'ww'])

    def test_13_user_edits_stopped(self):
        self._test_cant('edit', self.mrloggedin, ['--', 'r-', 'rr'])
    def test_04_user_edits(self):
        self._test_can('edit', self.mrloggedin, ['w-', 'wr', 'ww'])

    def test_admin_edit_deleted(self):
        self._test_can('edit', self.admin, ['--', 'r-', 'w-', 'rr', 'wr', 'ww', 'deleted'])
        self._test_cant('edit', self.mrloggedin, ['deleted'])

    def test_admin_read_deleted(self):
        self._test_can('read', self.admin, ['--', 'r-', 'w-', 'rr', 'wr', 'ww', 'deleted'])
        self._test_cant('read', self.mrloggedin, ['deleted'])

    def test_admin_search_deleted(self):
        self._test_can('search', self.admin, ['--', 'r-', 'w-', 'rr', 'wr', 'ww', 'deleted'])
        self._test_can('search', self.mrloggedin, ['--', 'r-', 'w-', 'rr', 'wr', 'ww'])
        #TODO get this working
        #self._test_cant('search', self.mrloggedin, ['deleted'])
        
    def test_admin_list_deleted(self):
        self._test_can('list', self.admin, ['--', 'r-', 'w-', 'rr', 'wr', 'ww', 'deleted'], test=['wui'])
        self._test_can('list', self.mrloggedin, ['--', 'r-', 'w-', 'rr', 'wr', 'ww'], test=['wui'])
        #TODO get this working
        self._test_cant('list', self.mrloggedin, ['deleted'], test=['wui'])

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

