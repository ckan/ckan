from time import time
from copy import copy
from ckan.model import Role, Action

import sqlalchemy as sa
import ckan.model as model
from ckan.model import authz as mauthz
from ckan.tests import TestController, TestSearchIndexer, url_for
from ckan.lib.base import *
from ckan.lib.create_test_data import CreateTestData
import ckan.authz as authz
from ckan.lib.helpers import json

class AuthzTestBase(object):
    @classmethod
    def setup_class(self):
        indexer = TestSearchIndexer()
        self._create_test_data()
        model.Session.remove()
        indexer.index()

    @classmethod
    def teardown_class(self):
        model.Session.remove()
        model.repo.rebuild_db()
        model.Session.remove()

    def _test_can(self, action, users, entity_names, interfaces=['wui', 'rest'], entity_types=['package', 'group']):
        if isinstance(users, model.User):
            users = [users]
        if isinstance(entity_names, basestring):
            entity_names = [entity_names]            
        for user in users:
            for entity_name in entity_names:
                if 'wui' in interfaces:
                    for entity_type in entity_types:
                        ok_wui = self._test_via_wui(action, user, entity_name, entity_type)
                        assert ok_wui, 'Should be able to %s %s %r as user %r (WUI interface)' % (action, entity_type, entity_name, user.name)
                if 'rest' in interfaces:
                    for entity_type in entity_types:
                        ok_rest = self._test_via_api(action, user, entity_name, entity_type)
                        assert ok_rest, 'Should be able to %s %s %r as user %r (REST interface)' % (action, entity_type, entity_name, user.name)

    def _test_cant(self, action, users, entity_names, interfaces=['wui', 'rest'], entity_types=['package', 'group']):
        if isinstance(users, model.User):
            users = [users]
        if isinstance(entity_names, basestring):
            entity_names = [entity_names]            
        for user in users:
            for entity_name in entity_names:
                if 'wui' in interfaces:
                    for entity_type in entity_types:
                        ok_wui = self._test_via_wui(action, user, entity_name, entity_type)
                        assert not ok_wui, 'Should NOT be able to %s %s %r as user %r (WUI interface)' % (action, entity_type, entity_name, user.name)
                if 'rest' in interfaces:
                    for entity_type in entity_types:
                        ok_rest = self._test_via_api(action, user, entity_name)
                        assert not ok_rest, 'Should NOT be able to %s %s %r as user %r (REST interface)' % (action, entity_type, entity_name, user.name)

    def _test_via_wui(self, action, user, entity_name, entity='package'):
        # Test action on WUI
        str_required_in_response = entity_name
        if action in (model.Action.EDIT, model.Action.READ):
            offset = url_for(controller=entity, action=action, id=unicode(entity_name))
        elif action == 'search':
            offset = '/%s/search?q=%s' % (entity, entity_name)
            str_required_in_response = '/%s"' % entity_name
        elif action == 'list':
            if entity == 'group':
                offset = '/group'
            else:
                offset = '/%s/list' % entity
        elif action == 'create':
            offset = '/%s/new' % entity
            str_required_in_response = 'New'
        else:
            raise NotImplementedError
        res = self.app.get(offset, extra_environ={'REMOTE_USER': user.name.encode('utf8')}, expect_errors=True)
        is_ok = str_required_in_response in res and u'error' not in res and res.status in (200, 201) and not '0 packages found' in res
        # clear flash messages - these might make the next page request
        # look like it has an error
        self.app.reset()
        return is_ok

    def _test_via_api(self, action, user, entity_name, entity='package'):
        # Test action on REST
        str_required_in_response = entity_name
        if action == model.Action.EDIT:
            offset = '/api/rest/%s/%s' % (entity, entity_name)
            postparams = '%s=1' % json.dumps({'title':u'newtitle'}, encoding='utf8')
            func = self.app.post
        elif action == model.Action.READ:
            offset = '/api/rest/%s/%s' % (entity, entity_name)
            postparams = None
            func = self.app.get
        elif action == 'search':
            offset = '/api/search/%s?q=%s' % (entity, entity_name)
            postparams = None
            func = self.app.get
        elif action == 'list':
            offset = '/api/rest/%s' % (entity)
            postparams = None
            func = self.app.get
        elif action == 'create':
            offset = '/api/rest/%s' % (entity)
            postparams = '%s=1' % json.dumps({'name': u'%s-%s' % (entity_name, int(time())), 
                                              'title': u'newtitle'}, encoding='utf8')
            func = self.app.post
            str_required_in_response = ''
        elif action == 'delete':
            offset = '/api/rest/%s/%s' % (entity, entity_name)
            func = self.app.delete
            postparams = {}
            str_required_in_response = ''
        else:
            raise NotImplementedError, action
        if user.name == 'visitor':
            environ = {}
        else:
            environ = {'Authorization' : str(user.apikey)}
        res = func(offset, params=postparams,
                   extra_environ=environ,
                   expect_errors=True)
        return str_required_in_response in res and u'error' not in res and res.status in (200, 201) and u'0 packages found' not in res

class TestUsage(TestController, AuthzTestBase):
    @classmethod
    def _create_test_data(self):
        # Mode pairs:
        #   First letter is for logged in users
        #   Second letter is for visitors
        # Where:
        #   r = Allowed to read
        #   w = Allowed to read/write
        #   x = Not allowed either
        model.repo.init_db()
        rev = model.repo.new_revision()
        self.modes = ('xx', 'rx', 'wx', 'rr', 'wr', 'ww', 'deleted')
        tag = model.Tag("test")
        model.Session.add(tag)
        for mode in self.modes:
            pkg = model.Package(name=unicode(mode))
            model.Session.add(pkg)
            pkg.tags.append(tag)
            model.Session.add(model.Group(name=unicode(mode)))
        
        model.Session.add(model.Package(name=u'delete_visitor_rest'))
        model.Session.add(model.Package(name=u'delete_admin_rest'))
        
        model.Session.add(model.User(name=u'testsysadmin'))
        model.Session.add(model.User(name=u'pkggroupadmin'))
        model.Session.add(model.User(name=u'pkgeditor'))
        model.Session.add(model.User(name=u'pkgreader'))
        model.Session.add(model.User(name=u'mrloggedin'))
        model.Session.add(model.User(name=u'pkgadminfriend'))
        model.Session.add(model.User(name=u'groupadmin'))
        model.Session.add(model.User(name=u'groupeditor'))
        model.Session.add(model.User(name=u'groupreader'))
        visitor_name = '123.12.12.123'
        model.repo.commit_and_remove()

        testsysadmin = model.User.by_name(u'testsysadmin')
        pkggroupadmin = model.User.by_name(u'pkggroupadmin')
        pkgeditor = model.User.by_name(u'pkgeditor')
        pkgreader = model.User.by_name(u'pkgreader')
        groupadmin = model.User.by_name(u'groupadmin')
        groupeditor = model.User.by_name(u'groupeditor')
        groupreader = model.User.by_name(u'groupreader')
        mrloggedin = model.User.by_name(name=u'mrloggedin')
        visitor = model.User.by_name(name=model.PSEUDO_USER__VISITOR)
        for mode in self.modes:
            pkg = model.Package.by_name(unicode(mode))
            model.add_user_to_role(pkggroupadmin, model.Role.ADMIN, pkg)
            model.add_user_to_role(pkgeditor, model.Role.EDITOR, pkg)
            model.add_user_to_role(pkgreader, model.Role.READER, pkg)
            group = model.Group.by_name(unicode(mode))
            group.packages = model.Session.query(model.Package).all()
            model.add_user_to_role(pkggroupadmin, model.Role.ADMIN, group)
            model.add_user_to_role(groupadmin, model.Role.ADMIN, group)
            model.add_user_to_role(groupeditor, model.Role.EDITOR, group)
            model.add_user_to_role(groupreader, model.Role.READER, group)
            if mode == u'deleted':
                rev = model.repo.new_revision()
                pkg = model.Package.by_name(unicode(mode))
                pkg.state = model.State.DELETED
                group = model.Package.by_name(unicode(mode))
                group.state = model.State.DELETED
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
        self.pkggroupadmin = model.User.by_name(u'pkggroupadmin')
        self.pkgadminfriend = model.User.by_name(u'pkgadminfriend')
        self.pkgeditor = model.User.by_name(u'pkgeditor')
        self.pkgreader = model.User.by_name(u'pkgreader')
        self.groupadmin = model.User.by_name(u'groupadmin')
        self.groupeditor = model.User.by_name(u'groupeditor')
        self.groupreader = model.User.by_name(u'groupreader')
        self.mrloggedin = model.User.by_name(name=u'mrloggedin')
        self.visitor = model.User.by_name(name=model.PSEUDO_USER__VISITOR)
        
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
        # NB this no listing of package in wui interface any more
        self._test_can('list', [self.testsysadmin, self.pkggroupadmin], ['xx', 'rx', 'wx', 'rr', 'wr', 'ww'], entity_types=['package'], interfaces=['rest'])
        self._test_can('list', [self.testsysadmin, self.groupadmin], ['xx', 'rx', 'wx', 'rr', 'wr', 'ww'], entity_types=['group'])
        self._test_can('list', self.mrloggedin, ['rx', 'wx', 'rr', 'wr', 'ww'], interfaces=['rest'])
        self._test_can('list', self.visitor, ['rr', 'wr', 'ww'], interfaces=['rest'])
        self._test_cant('list', self.mrloggedin, ['xx'])
        self._test_cant('list', self.visitor, ['xx', 'rx', 'wx'])

    def test_admin_edit_deleted(self):
        self._test_can('edit', self.pkggroupadmin, ['xx', 'rx', 'wx', 'rr', 'wr', 'ww', 'deleted'])
        self._test_cant('edit', self.mrloggedin, ['deleted'])

    def test_admin_read_deleted(self):
        self._test_can('read', self.pkggroupadmin, ['xx', 'rx', 'wx', 'rr', 'wr', 'ww', 'deleted'])
        self._test_cant('read', self.mrloggedin, ['deleted'])

    def test_search_deleted(self):
        self._test_can('search', self.pkggroupadmin, ['xx', 'rx', 'wx', 'rr', 'wr', 'ww', 'deleted'], entity_types=['package'])
        self._test_can('search', self.mrloggedin, ['rx', 'wx', 'rr', 'wr', 'ww'], entity_types=['package'])
        self._test_cant('search', self.mrloggedin, ['deleted', 'xx'], entity_types=['package'])
        
    def test_05_author_is_new_package_admin(self):
        user = self.mrloggedin
        
        # make new package
        assert not model.Package.by_name(u'annakarenina')
        offset = url_for(controller='package', action='new')
        res = self.app.get(offset, extra_environ={'REMOTE_USER': user.name.encode('utf8')})
        assert 'New - Data Packages' in res
        fv = res.forms['package-edit']
        prefix = 'Package--'
        fv[prefix + 'name'] = u'annakarenina'
        res = fv.submit('save', extra_environ={'REMOTE_USER': user.name.encode('utf8')})

        # check user is admin
        pkg = model.Package.by_name(u'annakarenina')
        assert pkg
        roles = authz.Authorizer().get_roles(user.name, pkg)
        assert model.Role.ADMIN in roles, roles
        roles = authz.Authorizer().get_roles(u'someoneelse', pkg)
        assert not model.Role.ADMIN in roles, roles

    def test_sysadmin_can_read_anything(self):
        self._test_can('read', self.testsysadmin, ['xx', 'rx', 'wx', 'rr', 'wr', 'ww', 'deleted'])
        
    def test_sysadmin_can_edit_anything(self):
        self._test_can('edit', self.testsysadmin, ['xx', 'rx', 'wx', 'rr', 'wr', 'ww', 'deleted'])
        
    def test_sysadmin_can_search_anything(self):
        self._test_can('search', self.testsysadmin, ['xx', 'rx', 'wx', 'rr', 'wr', 'ww', 'deleted'], entity_types=['package'])
        
    def test_visitor_creates(self): 
        self._test_can('create', self.visitor, ['rr'], interfaces=['wui'], entity_types=['package'])

    def test_user_creates(self):
        self._test_can('create', self.mrloggedin, ['rr'])
        
    def test_visitor_deletes(self):
        pkg = model.Package.by_name(u'delete_admin_rest')
        assert pkg is not None
        self._test_cant('delete', self.visitor, [str(pkg.id)], interfaces=['rest'], entity_types=['package'])
        
    def test_sysadmin_deletes(self):
        pkg = model.Package.by_name(u'delete_admin_rest')
        assert pkg is not None
        self._test_can('delete', self.testsysadmin, [str(pkg.id)], interfaces=['rest'], entity_types=['package'])
    

class TestSiteRead(TestController, AuthzTestBase):
    '''User case:
           * 'Visitor' and 'Logged in' cannot SITE_READ System
           * 'TrustedRole' is a new Role that can SITE_READ System

    '''
    TRUSTED_ROLE = u'TrustedRole'
    ENTITY_NAME = u'test'
    @classmethod
    def _create_test_data(cls):
        CreateTestData.create()

        # Remove visitor and logged in roles
        roles = []
        q = model.Session.query(model.UserObjectRole).\
            filter(model.UserObjectRole.user==model.User.by_name(u"visitor"))
        roles.extend(q.all())
        q = model.Session.query(model.UserObjectRole).\
            filter(model.UserObjectRole.user==model.User.by_name(u"logged_in"))
        roles.extend(q.all())
        for role in roles:
            model.Session.delete(role)

        rev = model.repo.new_revision()
        model.Session.add_all([
            model.User(name=u'pkggroupadmin'),
            model.User(name=u'site_reader'),
            model.User(name=u'outcast'),
            model.Package(name=cls.ENTITY_NAME),
            model.Package(name=u'deleted'),
            model.Group(name=cls.ENTITY_NAME),
            model.Group(name=u'deleted'),
            model.Tag(name=cls.ENTITY_NAME),
            model.RoleAction(role=cls.TRUSTED_ROLE, context=u'',
                             action=model.Action.SITE_READ),
            model.RoleAction(role=cls.TRUSTED_ROLE, context=u'',
                             action=model.Action.READ),
            ])
        model.repo.commit_and_remove()

        # testsysadmin is sysadmin
        # annafan is package admin for annakarenina
        rev = model.repo.new_revision()
        site_reader = model.User.by_name(u'site_reader')
        pkggroupadmin = model.User.by_name(u'pkggroupadmin')
        pkg = model.Package.by_name(cls.ENTITY_NAME)
        group = model.Group.by_name(cls.ENTITY_NAME)
        tag = model.Tag.by_name(cls.ENTITY_NAME)
        pkg.tags.append(tag)
        model.add_user_to_role(site_reader, cls.TRUSTED_ROLE, model.System())
        model.add_user_to_role(site_reader, cls.TRUSTED_ROLE, pkg)
        model.add_user_to_role(site_reader, cls.TRUSTED_ROLE, group)
        model.add_user_to_role(pkggroupadmin, model.Role.ADMIN, pkg)
        model.add_user_to_role(pkggroupadmin, model.Role.ADMIN, group)
        model.Package.by_name(u'deleted').delete()
        model.Group.by_name(u'deleted').delete()
        model.repo.commit_and_remove()

        cls.testsysadmin = model.User.by_name(u'testsysadmin')
        cls.pkggroupadmin = model.User.by_name(u'pkggroupadmin')
        cls.site_reader = model.User.by_name(u'site_reader')
        cls.outcast = model.User.by_name(u'outcast')

    def test_sysadmin_can_read_anything(self):
        self._test_can('read', self.testsysadmin, self.ENTITY_NAME)
        self._test_can('read', self.testsysadmin, 'deleted')

    def test_sysadmin_can_edit_anything(self):
        self._test_can('edit', self.testsysadmin, self.ENTITY_NAME)
        self._test_can('edit', self.testsysadmin, 'deleted')

    def test_sysadmin_can_search_anything(self):
        self._test_can('search', self.testsysadmin, self.ENTITY_NAME, entity_types=['package']) # cannot search groups

    def test_pkggroupadmin_read(self):
        # These don't make sense - there should be no difference between
        # read/write in WUI and REST interface.
        self._test_can('read', self.pkggroupadmin, self.ENTITY_NAME, interfaces=['wui'])
        self._test_cant('read', self.pkggroupadmin, self.ENTITY_NAME, interfaces=['rest'])
        self._test_cant('read', self.pkggroupadmin, 'deleted')

    def test_pkggroupadmin_edit(self):
        # These don't make sense - there should be no difference between
        # read/write in WUI and REST interface.
        self._test_can('edit', self.pkggroupadmin, self.ENTITY_NAME, interfaces=['wui'])
        self._test_cant('edit', self.pkggroupadmin, self.ENTITY_NAME, interfaces=['rest'])
        self._test_cant('edit', self.pkggroupadmin, 'deleted')

    def test_pkggroupadmin_search(self):
        # can't search as not a site reader
        self._test_cant('search', self.pkggroupadmin, self.ENTITY_NAME, entity_types=['package'])

    def test_site_reader(self):
        self._test_can('search', self.site_reader, self.ENTITY_NAME, entity_types=['package']) # cannot search groups
        self._test_can('read', self.site_reader, self.ENTITY_NAME, entity_types=['tag'])

    def test_outcast_search(self):
        self._test_cant('search', self.outcast, self.ENTITY_NAME, entity_types=['package']) # cannot search groups
        self._test_cant('read', self.outcast, self.ENTITY_NAME, entity_types=['tag'])

        
class TestLockedDownUsage(TestController):
    '''Use case:
           * 'Visitor' has no rights
           * 'Reader' role is redefined to not be able to read (!)

    '''
    @classmethod
    def setup_class(self):
        model.repo.init_db()
        q = model.Session.query(model.UserObjectRole).filter(model.UserObjectRole.role==Role.EDITOR)
        q = q.filter(model.UserObjectRole.user==model.User.by_name(u"visitor"))
        for role in q:
            model.Session.delete(role)
        
        q = model.Session.query(model.RoleAction).filter(model.RoleAction.role==Role.READER)
        for role_action in q:
            model.Session.delete(role_action)
        
        model.repo.commit_and_remove()
        indexer = TestSearchIndexer()
        TestUsage._create_test_data()
        model.Session.remove()
        indexer.index()
        self.user_name = TestUsage.mrloggedin.name.encode('utf-8')
    
    def _check_logged_in_users_authorized_only(self, offset):
        '''Checks the offset is accessible to logged in users only.'''
        res = self.app.get(offset, extra_environ={})
        assert res.status not in [200], res.status
        res = self.app.get(offset, extra_environ={'REMOTE_USER': self.user_name})
        assert res.status in [200], res.status

    def test_home(self):
        self._check_logged_in_users_authorized_only('/')
        self._check_logged_in_users_authorized_only('/about')
        self._check_logged_in_users_authorized_only('/license')
    
    def test_tags_pages(self):
        self._check_logged_in_users_authorized_only('/tag')
        self._check_logged_in_users_authorized_only('/tag/test')

    def test_revision_pages(self):
        self._check_logged_in_users_authorized_only('/revision')

    def test_user_pages(self):
        self._check_logged_in_users_authorized_only('/user')
        self._check_logged_in_users_authorized_only('/user/' + self.user_name)
        res = self.app.get('/user/login', extra_environ={})
        assert res.status in [200], res.status
        #res = self.app.get('/user/register', extra_environ={})
        #assert res.status in [200], res.status
    
    def test_new_package(self):
        offset = url_for(controller='package', action='new')
        self._check_logged_in_users_authorized_only(offset)

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()
        model.Session.remove()
