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
            model.Group(name=unicode(mode))
        model.User(name=u'testsysadmin') # in test.ini
        model.User(name=u'pkgadmin')
        model.User(name=u'pkgeditor')
        model.User(name=u'pkgreader')
        model.User(name=u'mrloggedin')
        model.User(name=u'pkgadminfriend')
        model.User(name=u'groupadmin')
        model.User(name=u'groupeditor')
        model.User(name=u'groupreader')
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
            group = model.Group.by_name(unicode(mode))
            group.packages = [pkg1 for pkg1 in model.Package.query.all()]
            model.add_user_to_role(pkgadmin, model.Role.ADMIN, pkg)
            model.add_user_to_role(pkgeditor, model.Role.EDITOR, pkg)
            model.add_user_to_role(pkgreader, model.Role.READER, pkg)
            model.add_user_to_role(groupadmin, model.Role.ADMIN, group)
            model.add_user_to_role(groupeditor, model.Role.EDITOR, group)
            model.add_user_to_role(groupreader, model.Role.READER, group)
            if mode == u'deleted':
                pkg.state = model.State.query.filter_by(name='deleted').one()
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
        model.repo.commit_and_remove()

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
        if action in (model.Action.EDIT, model.Action.READ):
            offset = url_for(controller=entity, action=action, id=unicode(mode))
        elif action == 'search':
            offset = '/%s/search?q=%s' % (entity, mode)
        elif action == 'list':
            if entity == 'group':
                offset = '/group'
            else:
                offset = '/%s/list' % entity
        else:
            raise NotImplementedError
        res = self.app.get(offset, extra_environ={'REMOTE_USER': user.name.encode('utf8')}, expect_errors=True)
        is_ok = mode in res and u'error' not in res and res.status==200 and not '0 packages found' in res
        return is_ok

    def _do_test_rest(self, action, user, mode, entity='package'):
        # Test action on REST
        if action == model.Action.EDIT:
            offset = '/api/rest/%s/%s' % (entity, mode)
            postparams = '%s=1' % simplejson.dumps({'title':u'newtitle'})
            func = self.app.post
        elif action == model.Action.READ:
            offset = '/api/rest/%s/%s' % (entity, mode)
            postparams = None
            func = self.app.get
        elif action == 'search':
            offset = '/api/search/%s?q=%s' % (entity, mode)
            postparams = None
            func = self.app.get
        else:
            raise NotImplementedError
        if user.name == 'visitor':
            environ = {}
        else:
            environ = {'Authorization' : str(user.apikey)}
        res = func(offset, params=postparams,
                   extra_environ=environ,
                   expect_errors=True)
        return mode in res and u'error' not in res and res.status==200 and u'0 packages found' not in res
        
    def _test_can(self, action, user, modes, interfaces=['wui', 'rest'], entities=['package', 'group']):
        for i, mode in enumerate(modes):
            if 'wui' in interfaces:
                for entity in entities:
                    ok_wui = self._do_test_wui(action, user, mode, entity)
                    assert ok_wui, '(%i) Should be able to %s %s %r as user %r (WUI interface)' % (i, action, entity, mode, user.name)
            if 'rest' in interfaces:
                for entity in entities:
                    ok_rest = self._do_test_rest(action, user, mode, entity)
                    assert ok_rest, '(%i) Should be able to %s %s %r as user %r (REST interface)' % (i, action, entity, mode, user.name)

    def _test_cant(self, action, user, modes, interfaces=['wui', 'rest'], entities=['package', 'group']):
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
        self._test_cant('read', self.visitor, ['--', 'r-', 'w-'])
    def test_01_visitor_reads(self): 
        self._test_can('read', self.visitor, ['rr', 'wr', 'ww'])

    def test_12_visitor_edits_stopped(self):
        self._test_cant('edit', self.visitor, ['ww'], interfaces=['rest'])
        self._test_cant('edit', self.visitor, ['--', 'r-', 'w-', 'rr', 'wr'], interfaces=['wui'])
        self._test_cant('edit', self.visitor, ['--', 'r-', 'w-', 'rr', 'wr', 'ww'], interfaces=['rest'])
    def test_02_visitor_edits(self):
        self._test_can('edit', self.visitor, ['ww'], interfaces=['wui'])
        self._test_can('edit', self.visitor, [], interfaces=['rest'])

    def test_15_user_reads_stopped(self):
        self._test_cant('read', self.mrloggedin, ['--'])
    def test_03_user_reads(self):
        self._test_can('read', self.mrloggedin, ['r-', 'w-', 'rr', 'wr', 'ww'])

    def test_13_user_edits_stopped(self):
        self._test_cant('edit', self.mrloggedin, ['--', 'r-', 'rr'])
    def test_04_user_edits(self):
        self._test_can('edit', self.mrloggedin, ['w-', 'wr', 'ww'])

    def test_admin_edit_deleted(self):
        self._test_can('edit', self.pkgadmin, ['--', 'r-', 'w-', 'rr', 'wr', 'ww', 'deleted'], entities=['package'])
        self._test_can('edit', self.groupadmin, ['--', 'r-', 'w-', 'rr', 'wr', 'ww', 'deleted'], entities=['group'])
        self._test_cant('edit', self.mrloggedin, ['deleted'])

    def test_admin_read_deleted(self):
        self._test_can('read', self.pkgadmin, ['--', 'r-', 'w-', 'rr', 'wr', 'ww', 'deleted'], entities=['package'])
        self._test_can('read', self.groupadmin, ['--', 'r-', 'w-', 'rr', 'wr', 'ww', 'deleted'], entities=['group'])
        self._test_cant('read', self.mrloggedin, ['deleted'])

    def test_search_deleted(self):
        self._test_can('search', self.pkgadmin, ['--', 'r-', 'w-', 'rr', 'wr', 'ww', 'deleted'], entities=['package'])
        self._test_can('search', self.mrloggedin, ['r-', 'w-', 'rr', 'wr', 'ww'], entities=['package'])
        #TODO get this working
        #self._test_cant('search', self.mrloggedin, ['--', 'deleted'], entities=['package'])
        
    def test_list_deleted(self):
        self._test_can('list', self.pkgadmin, ['--', 'r-', 'w-', 'rr', 'wr', 'ww', 'deleted'], interfaces=['wui'], entities=['package'])
        self._test_can('list', self.mrloggedin, ['r-', 'w-', 'rr', 'wr', 'ww'], interfaces=['wui'])
        #TODO get this working
        #self._test_cant('list', self.mrloggedin, ['--', 'deleted'], interfaces=['wui'])

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

