import simplejson

import ckan.model as model
from ckan.tests import *
from ckan.lib.base import *
import ckan.authz as authz

class TestUsage(TestController):
    deleted = model.State.DELETED
    active = model.State.ACTIVE
    
    @classmethod
    def _create_test_data(self):
        # Mode pairs:
        #   First letter is for logged in users
        #   Second letter is for visitors
        # Where:
        #   r = Allowed to read
        #   w = Allowed to read/write
        #   x = Not allowed either
        self.modes = ('xx', 'rx', 'wx', 'rr', 'wr', 'ww', 'deleted')
        for mode in self.modes:
            model.Session.add(model.Package(name=unicode(mode)))
            if mode != 'deleted':
                # Groups aren't stateful
                model.Session.add(model.Group(name=unicode(mode)))
        model.Session.add(model.User(name=u'testsysadmin'))
        model.Session.add(model.User(name=u'pkgadmin'))
        model.Session.add(model.User(name=u'pkgeditor'))
        model.Session.add(model.User(name=u'pkgreader'))
        model.Session.add(model.User(name=u'mrloggedin'))
        model.Session.add(model.User(name=u'pkgadminfriend'))
        model.Session.add(model.User(name=u'groupadmin'))
        model.Session.add(model.User(name=u'groupeditor'))
        model.Session.add(model.User(name=u'groupreader'))
        visitor_name = '123.12.12.123'
        rev = model.repo.new_revision()
        model.repo.commit_and_remove()

        testsysadmin = model.User.by_name(u'testsysadmin')
        pkgadmin = model.User.by_name(u'pkgadmin')
        pkgeditor = model.User.by_name(u'pkgeditor')
        pkgreader = model.User.by_name(u'pkgreader')
        groupadmin = model.User.by_name(u'groupadmin')
        groupeditor = model.User.by_name(u'groupeditor')
        groupreader = model.User.by_name(u'groupreader')
        mrloggedin = model.User.by_name(name=u'mrloggedin')
        visitor = model.User.by_name(name=model.PSEUDO_USER__VISITOR)
        for mode in self.modes:
            pkg = model.Package.by_name(unicode(mode))
            model.add_user_to_role(pkgadmin, model.Role.ADMIN, pkg)
            model.add_user_to_role(pkgeditor, model.Role.EDITOR, pkg)
            model.add_user_to_role(pkgreader, model.Role.READER, pkg)
            if mode != 'deleted':
                group = model.Group.by_name(unicode(mode))
                group.packages = model.Session.query(model.Package).all()
                model.add_user_to_role(groupadmin, model.Role.ADMIN, group)
                model.add_user_to_role(groupeditor, model.Role.EDITOR, group)
                model.add_user_to_role(groupreader, model.Role.READER, group)
            if mode == u'deleted':
                pkg = model.Package.by_name(unicode(mode))
                pkg.state = model.State.DELETED
                rev = model.repo.new_revision()
                model.repo.commit_and_remove()
            else:
                if mode[0] == u'r':
                    model.add_user_to_role(mrloggedin, model.Role.READER, pkg)
                    model.add_user_to_role(mrloggedin, model.Role.READER, group)
                if mode[0] == u'w':
                    model.add_user_to_role(mrloggedin, model.Role.EDITOR, pkg)
                    model.add_user_to_role(mrloggedin, model.Role.EDITOR, group)
                if mode[1] == u'r':
                    model.add_user_to_role(visitor, model.Role.READER, pkg)
                    model.add_user_to_role(visitor, model.Role.READER, group)
                if mode[1] == u'w':
                    model.add_user_to_role(visitor, model.Role.EDITOR, pkg)
                    model.add_user_to_role(visitor, model.Role.EDITOR, group)
        model.add_user_to_role(testsysadmin, model.Role.ADMIN, model.System())
        model.repo.commit_and_remove()

        assert model.Package.by_name(u'deleted').state == model.State.DELETED

        self.testsysadmin = model.User.by_name(u'testsysadmin')
        self.pkgadmin = model.User.by_name(u'pkgadmin')
        self.pkgadminfriend = model.User.by_name(u'pkgadminfriend')
        self.pkgeditor = model.User.by_name(u'pkgeditor')
        self.pkgreader = model.User.by_name(u'pkgreader')
        self.groupadmin = model.User.by_name(u'groupadmin')
        self.groupeditor = model.User.by_name(u'groupeditor')
        self.groupreader = model.User.by_name(u'groupreader')
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

    def _do_test_wui(self, action, user, mode, entity='package'):
        # Test action on WUI
        search_for = mode
        if action in (model.Action.EDIT, model.Action.READ):
            offset = url_for(controller=entity, action=action, id=unicode(mode))
        elif action == 'search':
            offset = '/%s/search?q=%s' % (entity, mode)
            search_for = '/%s"' % mode
        elif action == 'list':
            if entity == 'group':
                offset = '/group'
            else:
                offset = '/%s/list' % entity
        else:
            raise NotImplementedError
        res = self.app.get(offset, extra_environ={'REMOTE_USER': user.name.encode('utf8')}, expect_errors=True)
        is_ok = search_for in res and u'error' not in res and res.status==200 and not '0 packages found' in res
        return is_ok

    def _do_test_rest(self, action, user, mode, entity='package'):
        # Test action on REST
        if action == model.Action.EDIT:
            offset = '/api/rest/%s/%s' % (entity, mode)
            postparams = '%s=1' % simplejson.dumps({'title':u'newtitle'}, encoding='utf8')
            func = self.app.post
        elif action == model.Action.READ:
            offset = '/api/rest/%s/%s' % (entity, mode)
            postparams = None
            func = self.app.get
        elif action == 'search':
            offset = '/api/search/%s?q=%s' % (entity, mode)
            postparams = None
            func = self.app.get
        elif action == 'list':
            offset = '/api/rest/%s' % (entity)
            postparams = None
            func = self.app.get
        else:
            raise NotImplementedError, action
        if user.name == 'visitor':
            environ = {}
        else:
            environ = {'Authorization' : str(user.apikey)}
        res = func(offset, params=postparams,
                   extra_environ=environ,
                   expect_errors=True)
        return mode in res and u'error' not in res and res.status==200 and u'0 packages found' not in res
        
    def _test_can(self, action, users, modes, interfaces=['wui', 'rest'], entities=['package', 'group']):
        if isinstance(users, model.User):
            users = [users]
        for user in users:
            for i, mode in enumerate(modes):
                if 'wui' in interfaces:
                    for entity in entities:
                        ok_wui = self._do_test_wui(action, user, mode, entity)
                        assert ok_wui, '(%i) Should be able to %s %s %r as user %r (WUI interface)' % (i, action, entity, mode, user.name)
                if 'rest' in interfaces:
                    for entity in entities:
                        ok_rest = self._do_test_rest(action, user, mode, entity)
                        assert ok_rest, '(%i) Should be able to %s %s %r as user %r (REST interface)' % (i, action, entity, mode, user.name)

    def _test_cant(self, action, users, modes, interfaces=['wui', 'rest'], entities=['package', 'group']):
        if isinstance(users, model.User):
            users = [users]
        for user in users:
            for i, mode in enumerate(modes):
                if 'wui' in interfaces:
                    for entity in entities:
                        ok_wui = self._do_test_wui(action, user, mode, entity)
                        assert not ok_wui, '(%i) Should NOT be able to %s %s %r as user %r (WUI interface)' % (i, action, entity, mode, user.name)
                if 'rest' in interfaces:
                    for entity in entities:
                        ok_rest = self._do_test_rest(action, user, mode)
                        assert not ok_rest, '(%i) Should NOT be able to %s %s %r as user %r (REST interface)' % (i, action, entity, mode, user.name)

    # Tests numbered by the use case

    def test_14_visitor_reads_stopped(self):
        self._test_cant('read', self.visitor, ['xx', 'rx', 'wx'])
    def test_01_visitor_reads(self): 
        self._test_can('read', self.visitor, ['rr', 'wr', 'ww'])

    def test_12_visitor_edits_stopped(self):
        self._test_cant('edit', self.visitor, ['ww'], interfaces=['rest'])
        self._test_cant('edit', self.visitor, ['xx', 'rx', 'wx', 'rr', 'wr'], interfaces=['wui'])
        self._test_cant('edit', self.visitor, ['xx', 'rx', 'wx', 'rr', 'wr', 'ww'], interfaces=['rest'])
    def test_02_visitor_edits(self):
        self._test_can('edit', self.visitor, ['ww'], interfaces=['wui'])
        self._test_can('edit', self.visitor, [], interfaces=['rest'])

    def test_15_user_reads_stopped(self):
        self._test_cant('read', self.mrloggedin, ['xx'])
    def test_03_user_reads(self):
        self._test_can('read', self.mrloggedin, ['rx', 'wx', 'rr', 'wr', 'ww'])

    def test_13_user_edits_stopped(self):
        self._test_cant('edit', self.mrloggedin, ['xx', 'rx', 'rr'])
    def test_04_user_edits(self):
        self._test_can('edit', self.mrloggedin, ['wx', 'wr', 'ww'])

    def test_list(self):
        self._test_can('list', [self.testsysadmin, self.pkgadmin], ['xx', 'rx', 'wx', 'rr', 'wr', 'ww'], entities=['package'])
        self._test_can('list', [self.testsysadmin, self.groupadmin], ['xx', 'rx', 'wx', 'rr', 'wr', 'ww'], entities=['group'])
        self._test_can('list', self.mrloggedin, ['rx', 'wx', 'rr', 'wr', 'ww'])
        self._test_can('list', self.visitor, ['rr', 'wr', 'ww'])
        self._test_cant('list', self.mrloggedin, ['xx'])
        self._test_cant('list', self.visitor, ['xx', 'rx', 'wx'])

    def test_admin_edit_deleted(self):
        self._test_can('edit', self.pkgadmin, ['xx', 'rx', 'wx', 'rr', 'wr', 'ww', 'deleted'], entities=['package'])
        self._test_can('edit', self.groupadmin, ['xx', 'rx', 'wx', 'rr', 'wr', 'ww'], entities=['group'])
        self._test_cant('edit', self.mrloggedin, ['deleted'])

    def test_admin_read_deleted(self):
        self._test_can('read', self.pkgadmin, ['xx', 'rx', 'wx', 'rr', 'wr', 'ww', 'deleted'], entities=['package'])
        self._test_can('read', self.groupadmin, ['xx', 'rx', 'wx', 'rr', 'wr', 'ww'], entities=['group'])
        self._test_cant('read', self.mrloggedin, ['deleted'])

    def test_search_deleted(self):
        self._test_can('search', self.pkgadmin, ['xx', 'rx', 'wx', 'rr', 'wr', 'ww', 'deleted'], entities=['package'])
        self._test_can('search', self.mrloggedin, ['rx', 'wx', 'rr', 'wr', 'ww'], entities=['package'])
        self._test_cant('search', self.mrloggedin, ['deleted', 'xx'], entities=['package'])
        
    def test_list_deleted(self):
        self._test_can('list', self.pkgadmin, ['xx', 'rx', 'wx', 'rr', 'wr', 'ww', 'deleted'], interfaces=['wui'], entities=['package'])
        self._test_can('list', self.mrloggedin, ['rx', 'wx', 'rr', 'wr', 'ww'], interfaces=['wui'])
        self._test_cant('list', self.mrloggedin, ['deleted'], interfaces=['wui'])
        self._test_cant('list', self.mrloggedin, ['xx'], interfaces=['wui'], entities=['package'])

    def test_05_author_is_new_package_admin(self):
        user = self.mrloggedin
        
        # make new package
        assert not model.Package.by_name(u'annakarenina')
        offset = url_for(controller='package', action='new')
        res = self.app.get(offset, extra_environ={'REMOTE_USER': user.name.encode('utf8')})
        assert 'Packages - New' in res
        fv = res.forms[0]
        prefix = 'Package--'
        fv[prefix + 'name'] = u'annakarenina'
        res = fv.submit('commit', extra_environ={'REMOTE_USER': user.name.encode('utf8')})

        # check user is admin
        pkg = model.Package.by_name(u'annakarenina')
        assert pkg
        roles = authz.Authorizer().get_roles(user.name, pkg)
        assert model.Role.ADMIN in roles, roles
        roles = authz.Authorizer().get_roles(u'someoneelse', pkg)
        assert not model.Role.ADMIN in roles, roles

    def test_sysadmin_can_read_anything(self):
        self._test_can('read', self.testsysadmin, ['xx', 'rx', 'wx', 'rr', 'wr', 'ww'])
        self._test_can('read', self.testsysadmin, ['deleted'], entities=['package']) # groups not stateful
    def test_sysadmin_can_edit_anything(self):
        self._test_can('edit', self.testsysadmin, ['xx', 'rx', 'wx', 'rr', 'wr', 'ww'])
        self._test_can('edit', self.testsysadmin, ['deleted'], entities=['package'])
    def test_sysadmin_can_search_anything(self):
        self._test_can('search', self.testsysadmin, ['xx', 'rx', 'wx', 'rr', 'wr', 'ww', 'deleted'], entities=['package'])
    def test_sysadmin_can_list_anything(self):
        self._test_can('list', self.testsysadmin, ['xx', 'rx', 'wx', 'rr', 'wr', 'ww'], interfaces=['wui'])
        self._test_can('list', self.testsysadmin, ['deleted'], interfaces=['wui'], entities=['package'])
        
