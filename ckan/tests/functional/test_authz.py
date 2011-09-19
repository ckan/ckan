from time import time
from copy import copy
import random

import sqlalchemy as sa

import ckan.model as model
from ckan import plugins
from ckan.tests import TestController, url_for, setup_test_search_index
from ckan.lib.base import *
import ckan.lib.search as search
from ckan.lib.create_test_data import CreateTestData
import ckan.authz as authz
from ckan.lib.helpers import json, truncate

class AuthzTestBase(object):
    INTERFACES = ['wui', 'rest']
    DEFAULT_ENTITY_TYPES = ['dataset', 'group']
    ENTITY_CLASS_MAP = {'dataset': model.Package,
                        'group': model.Group,
                        'package_relationship': model.PackageRelationship}
        
    @classmethod
    def setup_class(self):
        setup_test_search_index()
        self._create_test_data()
        model.Session.remove()

    @classmethod
    def teardown_class(self):
        model.Session.remove()
        model.repo.rebuild_db()
        model.Session.remove()
        search.clear()

    def _test_can(self, action, users, entity_names,
                  interfaces=INTERFACES,
                  entity_types=DEFAULT_ENTITY_TYPES):
        self._test_expectation(action, users, entity_names,
                               interfaces=interfaces,
                               entity_types=entity_types,
                               expect_it_works=True)

    def _test_cant(self, action, users, entity_names,
                  interfaces=INTERFACES,
                  entity_types=DEFAULT_ENTITY_TYPES):
        self._test_expectation(action, users, entity_names,
                               interfaces=interfaces,
                               entity_types=entity_types,
                               expect_it_works=False)

    def _test_expectation(self, action, users, entity_names,
                          interfaces, entity_types,
                          expect_it_works):
        if isinstance(users, model.User):
            users = [users]
        if isinstance(entity_names, basestring):
            entity_names = [entity_names]
        if action == 'create' and 'package_relationship' not in entity_types:
            entity_names = [str(random.random()*100000000).replace('.', '-')]
        if action in ('delete', 'purge'):
            entity_names = ['filled in later']
        for user in users:
            for entity_name in entity_names:
                for interface in interfaces:
                    test_func = {'rest':self._test_via_api,
                                 'wui':self._test_via_wui}[interface]
                    for entity_type in entity_types:
                        if action in ('delete', 'purge'):
                            if entity_type != 'package_relationship':
                                entity_name = '%s_%s_%s' % (action, user.name, interface)
                                entity_class = self.ENTITY_CLASS_MAP[entity_type]
                            else:
                                raise NotImplementedError
                            entity = entity_class.by_name(entity_name)
                            assert entity, 'Have not created %s to %s: %r' %\
                                   (entity_type, action, entity_name)
                            entity_name = str(entity.id)
                        ok, diagnostics = test_func(action, user, entity_name, entity_type)
                        if ok != expect_it_works:
                            msg = 'Should be able to %s %s %r as user %r on %r interface. Diagnostics: %r' \
                                  if expect_it_works else \
                                  'Should NOT be able to %s %s %r as user %r on %r interface. Diagnostics: %r'
                            raise Exception(msg % (action, entity_type, entity_name, user.name, interface, truncate(repr(diagnostics), 1000)))

    def _test_via_wui(self, action, user, entity_name, entity='dataset'):
        # Test action on WUI
        str_required_in_response = entity_name
        controller_name = 'package' if entity == 'dataset' else entity

        if action in (model.Action.EDIT, model.Action.READ):
            offset = url_for(controller=controller_name, action=action, id=unicode(entity_name))
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
            if entity == 'dataset':
                str_required_in_response = 'Add'
            else:
                str_required_in_response = 'New'
        elif action == 'delete':
            offset = url_for(controller=controller_name, action=model.Action.EDIT, id=unicode(entity_name))
            # this is ludicrously sensitive (we have to improve html testing!)
            # str_required_in_response = 'state'
            str_required_in_response = '<select id="state"'
        else:
            raise NotImplementedError
        res = self.app.get(offset, extra_environ={'REMOTE_USER': user.name.encode('utf8')}, expect_errors=True)
        tests = {}
        tests['str_required (%s)' % str_required_in_response] = bool(str_required_in_response in res)
        tests['error string'] = bool('error' not in res)
        tests['status'] = bool(res.status in (200, 201))
        tests['0 packages found'] = bool(u'<strong>0</strong> packages found' not in res)
        is_ok = False not in tests.values()
        # clear flash messages - these might make the next page request
        # look like it has an error
        self.app.reset()
        return is_ok, [offset, user.name, tests, res.status, res.body]

    def _test_via_api(self, action, user, entity_name, entity_type='dataset'):
        # Test action on REST
        str_required_in_response = entity_name
        if action == model.Action.EDIT:
            offset = '/api/rest/%s/%s' % (entity_type, entity_name)
            postparams = '%s=1' % json.dumps({'title':u'newtitle'}, encoding='utf8')
            func = self.app.post
        elif action == model.Action.READ:
            offset = '/api/rest/%s/%s' % (entity_type, entity_name)
            postparams = None
            func = self.app.get
        elif action == 'search':
            offset = '/api/search/%s?q=%s' % (entity_type, entity_name)
            postparams = None
            func = self.app.get
        elif action == 'list':
            offset = '/api/rest/%s' % (entity_type)
            postparams = None
            func = self.app.get
        elif action == 'create':
            offset = '/api/rest/%s' % (entity_type)
            postparams = '%s=1' % json.dumps({'name': unicode(entity_name), 
                                              'title': u'newtitle'},
                                             encoding='utf8')
            func = self.app.post
            str_required_in_response = u'newtitle'
        elif action == 'delete':
            offset = '/api/rest/%s/%s' % (entity_type, entity_name)
            postparams = '%s=1' % json.dumps({'name': unicode(entity_name),
                                              'state': 'deleted'},
                                             encoding='utf8')
            func = self.app.post
            str_required_in_response = '"state": "deleted"'
            assert 0, 'Deleting in the API does not currently work - See #1053'
        elif action == 'purge':
            offset = '/api/rest/%s/%s' % (entity_type, entity_name)
            func = self.app.delete
            postparams = {}
            str_required_in_response = ''
        else:
            raise NotImplementedError, action
        if entity_type == 'package_relationship':
            if action == 'edit':
                func = self.app.put
            if isinstance(entity_name, basestring):
                offset = '/api/rest/dataset/%s/relationships' % entity_name
            else:
                assert isinstance(entity_name, tuple)
                if len(entity_name) == 1:
                    offset = '/api/rest/dataset/%s/relationships' % entity_name[0]
                else:
                    if len(entity_name) == 2:
                        entity_properties = {'entity1': entity_name[0],
                                             'entity2': entity_name[1],
                                             'type': 'relationships'}
                    elif len(entity_name) == 3:
                        entity_properties = {'entity1': entity_name[0],
                                             'entity2': entity_name[2],
                                             'type': entity_name[1]}
                    else:
                        raise NotImplementedError
                    if action in 'list':
                        offset = '/api/rest/dataset/%(entity1)s/relationships/%(entity2)s' % entity_properties
                    else:
                        offset = '/api/rest/dataset/%(entity1)s/%(type)s/%(entity2)s' % entity_properties
                    str_required_in_response = '"object": "%(entity2)s", "type": "%(type)s", "subject": "%(entity1)s"' % entity_properties
                
        if user.name == 'visitor':
            environ = {}
        else:
            environ = {'Authorization' : str(user.apikey)}
        res = func(offset, params=postparams,
                   extra_environ=environ,
                   expect_errors=True)
        tests = {}
        tests['str_required (%s)' % str_required_in_response] = bool(str_required_in_response in res)
        tests['error string'] = bool('error' not in res)
        tests['status'] = bool(res.status in (200, 201))
        tests['0 packages found'] = bool(u'0 packages found' not in res)
        is_ok = False not in tests.values()
        return is_ok, [offset, postparams, user.name, tests, res.status, res.body]

class TestUsage(TestController, AuthzTestBase):
    '''Use case: role defaults (e.g. like ckan.net operates)
       * reader can read only
       * editor can edit most properties of a package
       
    '''
    @classmethod
    def _create_test_data(cls):
        # Entities (Packages/Groups) are named after what roles (permissions)
        # are assigned to them:
        #   First letter is the role for logged in users
        #   Second letter is the role for visitors
        # Where:
        #   r = Allowed to read
        #   w = Allowed to read/write
        #   x = Not allowed either
        model.repo.init_db()
        rev = model.repo.new_revision()
        cls.roles = ('xx', 'rx', 'wx', 'rr', 'wr', 'ww', 'deleted')
        tag = model.Tag("test")
        model.Session.add(tag)
        for mode in cls.roles:
            pkg = model.Package(name=unicode(mode))
            model.Session.add(pkg)
            pkg.tags.append(tag)
            model.Session.add(model.Group(name=unicode(mode)))
        entities_to_test_deleting = []
        for interface in cls.INTERFACES:
            for action in ('purge', 'delete'):
                for user in ('visitor', 'user', 'admin',
                             'mrloggedin', 'testsysadmin',
                             'pkggroupadmin'):
                    for entity_type in cls.DEFAULT_ENTITY_TYPES:
                        entity_class = cls.ENTITY_CLASS_MAP[entity_type]
                        entity_name = u'%s_%s_%s' % (action, user, interface)
                        model.Session.add(entity_class(name=entity_name))
                        entities_to_test_deleting.append((entity_name, entity_class))
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

        rev = model.repo.new_revision()
        model.Package.by_name(u'ww').add_relationship(u'depends_on', model.Package.by_name(u'xx'))
        model.Package.by_name(u'ww').add_relationship(u'links_to', model.Package.by_name(u'wr'))
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
        for mode in cls.roles:
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
        for entity_name, entity_class in entities_to_test_deleting:
            entity = entity_class.by_name(entity_name)
            model.add_user_to_role(visitor, model.Role.EDITOR, entity)
            model.add_user_to_role(mrloggedin, model.Role.EDITOR, entity)
            model.add_user_to_role(visitor, model.Role.READER, entity)
            model.add_user_to_role(mrloggedin, model.Role.READER, entity)
            model.add_user_to_role(pkggroupadmin, model.Role.ADMIN, entity)
        
        model.repo.commit_and_remove()

        assert model.Package.by_name(u'deleted').state == model.State.DELETED

        cls.testsysadmin = model.User.by_name(u'testsysadmin')
        cls.pkggroupadmin = model.User.by_name(u'pkggroupadmin')
        cls.pkgadminfriend = model.User.by_name(u'pkgadminfriend')
        cls.pkgeditor = model.User.by_name(u'pkgeditor')
        cls.pkgreader = model.User.by_name(u'pkgreader')
        cls.groupadmin = model.User.by_name(u'groupadmin')
        cls.groupeditor = model.User.by_name(u'groupeditor')
        cls.groupreader = model.User.by_name(u'groupreader')
        cls.mrloggedin = model.User.by_name(name=u'mrloggedin')
        cls.visitor = model.User.by_name(name=model.PSEUDO_USER__VISITOR)

    # Tests numbered by the use case

    def test_14_visitor_reads_stopped(self):
        self._test_cant('read', self.visitor, ['xx', 'rx', 'wx'])
    def test_01_visitor_reads(self): 
        self._test_can('read', self.visitor, ['rr', 'wr', 'ww'])

    def test_12_visitor_edits_stopped(self):
        self._test_cant('edit', self.visitor, ['xx', 'rx', 'wx', 'rr', 'wr', 'ww'], interfaces=['rest'])
        self._test_cant('edit', self.visitor, ['xx', 'rx', 'wx', 'rr', 'wr'], interfaces=['wui'])
        
    def test_02_visitor_edits(self):
        self._test_can('edit', self.visitor, ['ww'], interfaces=['wui'])
        self._test_can('edit', self.visitor, [], interfaces=['rest'])

    def test_visitor_creates(self):
        self._test_can('create', self.visitor, [], interfaces=['wui'], entity_types=['dataset'])
        self._test_cant('create', self.visitor, [], interfaces=['wui'], entity_types=['group']) # need to be sysadmin
        self._test_cant('create', self.visitor, [], interfaces=['rest'])

    def test_15_user_reads_stopped(self):
        self._test_cant('read', self.mrloggedin, ['xx'])

    def test_03_user_reads(self):
        self._test_can('read', self.mrloggedin, ['rx', 'wx', 'rr', 'wr', 'ww'])

    def test_13_user_edits_stopped(self):
        self._test_cant('edit', self.mrloggedin, ['xx', 'rx', 'rr'])
    def test_04_user_edits(self):
        self._test_can('edit', self.mrloggedin, ['wx', 'wr', 'ww'])

    def test_user_creates(self):
        self._test_can('create', self.mrloggedin, [])
    
    def test_list(self):
        # NB there is no listing of package in wui interface any more
        # NB under the new model all active packages are always visible in listings by default
        self._test_can('list', [self.testsysadmin, self.pkggroupadmin, self.mrloggedin, self.visitor], ['xx', 'rx', 'wx', 'rr', 'wr', 'ww'], interfaces=['rest'])

    def test_admin_edit_deleted(self):
        self._test_can('edit', self.pkggroupadmin, ['xx', 'rx', 'wx', 'rr', 'wr', 'ww', 'deleted'])
        self._test_cant('edit', self.mrloggedin, ['deleted'])

    def test_admin_read_deleted(self):
        self._test_can('read', self.pkggroupadmin, ['xx', 'rx', 'wx', 'rr', 'wr', 'ww', 'deleted'])
        self._test_cant('read', self.mrloggedin, ['deleted'])

    def test_search_deleted(self):
        # can't search groups
        self._test_can('search', self.pkggroupadmin, ['xx', 'rx', 'wx', 'rr', 'wr', 'ww'], entity_types=['dataset'])
        self._test_can('search', self.mrloggedin, ['rx', 'wx', 'rr', 'wr', 'ww'], entity_types=['dataset'])

        # Solr search does not currently do authorized queries, so 'xx' will
        # be visible as user self.mrloggedin
        # TODO: Discuss authorized queries for packages and resolve this issue.
        # self._test_cant('search', self.mrloggedin, ['deleted', 'xx'], entity_types=['dataset'])
        self._test_cant('search', self.mrloggedin, ['deleted'], entity_types=['dataset'])
        
    def test_05_author_is_new_package_admin(self):
        user = self.mrloggedin
        
        # make new package
        assert not model.Package.by_name(u'annakarenina')
        offset = url_for(controller='package', action='new')
        res = self.app.get(offset, extra_environ={'REMOTE_USER': user.name.encode('utf8')})
        assert 'Add - Datasets' in res
        fv = res.forms['dataset-edit']
        prefix = ''
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
        
    def test_sysadmin_can_create_anything(self):
        self._test_can('create', self.testsysadmin, [])

    def test_sysadmin_can_search_anything(self):
        self._test_can('search', self.testsysadmin, ['xx', 'rx', 'wx', 'rr', 'wr', 'ww'], entity_types=['dataset'])
                
    def test_visitor_deletes(self):
        self._test_cant('delete', self.visitor, ['gets_filled'], interfaces=['wui'])

    def test_user_deletes(self):
        self._test_cant('delete', self.mrloggedin, ['gets_filled'], interfaces=['wui'])

    def test_admin_deletes(self):
        self._test_can('delete', self.pkggroupadmin, ['gets_filled'], interfaces=['wui'])

    def test_sysadmin_deletes(self):
        self._test_can('delete', self.testsysadmin, ['gets_filled'], interfaces=['wui'])

    def test_visitor_purges(self):
        self._test_cant('purge', self.visitor, ['gets_filled'], interfaces=['rest'])

    def test_user_purges(self):
        self._test_cant('purge', self.mrloggedin, ['gets_filled'], interfaces=['rest'])

    def test_admin_purges(self):
        self._test_can('purge', self.pkggroupadmin, ['gets_filled'], interfaces=['rest'])

    def test_sysadmin_purges(self):
        self._test_can('purge', self.testsysadmin, ['gets_filled'], interfaces=['rest'], entity_types=['dataset'])
    
    def test_sysadmin_relationships(self):
        opts = {'interfaces': ['rest'],
                'entity_types': ['package_relationship']}
        self._test_can('list', self.testsysadmin, [('ww')], **opts)
        self._test_can('list', self.testsysadmin, [('ww', 'links_to', 'wr'), ('ww', 'depends_on', 'xx')], **opts)
        self._test_can('create', self.testsysadmin, [('ww', 'child_of', 'wr'), ('ww', 'child_of', 'xx')], **opts)
        self._test_can('edit', self.testsysadmin, [('ww', 'links_to', 'wr'), ('ww', 'depends_on', 'xx')], **opts)
        #TODO self._test_can('delete', self.testsysadmin, [('ww', 'links_to', 'wr')], **opts)

    def test_admin_relationships(self):
        opts = {'interfaces': ['rest'],
                'entity_types': ['package_relationship']}
        self._test_can('list', self.pkggroupadmin, [('ww')], **opts)
        self._test_can('list', self.pkggroupadmin, [('ww', 'links_to', 'wr'), ('ww', 'depends_on', 'xx')], **opts)
        self._test_can('edit', self.pkggroupadmin, [('ww', 'links_to', 'wr'), ('ww', 'depends_on', 'xx')], **opts)
        #TODO self._test_can('delete', self.pkggroupadmin, [('ww', 'links_to', 'wr')], **opts)

    def test_user_relationships(self):
        opts = {'interfaces': ['rest'],
                'entity_types': ['package_relationship']}
        self._test_can('list', self.mrloggedin, [('ww')], **opts)
        self._test_can('list', self.mrloggedin, [('ww', 'links_to', 'wr')], **opts)
        self._test_cant('list', self.mrloggedin, [('ww', 'depends_on', 'xx')], **opts)
        self._test_can('create', self.mrloggedin, [('ww', 'derives_from', 'wr')], **opts)
        self._test_cant('create', self.mrloggedin, [('ww', 'derives_from', 'xx')], **opts)
        self._test_can('edit', self.mrloggedin, [('ww', 'links_to', 'wr')], **opts)
        self._test_cant('edit', self.mrloggedin, [('ww', 'depends_on', 'xx')], **opts)
        #TODO self._test_cant('delete', self.mrloggedin, [('ww', 'links_to', 'wr')], **opts)
        
    def test_visitor_relationships(self):
        opts = {'interfaces': ['rest'],
                'entity_types': ['package_relationship']}
        self._test_can('list', self.visitor, [('ww')], **opts)
        self._test_can('list', self.visitor, [('ww', 'links_to', 'wr')], **opts)
        self._test_cant('list', self.visitor, [('ww', 'depends_on', 'xx')], **opts)
        self._test_cant('create', self.visitor, [('ww', 'derives_from', 'wr'), ('ww', 'derives_from', 'xx')], **opts)
        self._test_cant('edit', self.visitor, [('ww', 'links_to', 'wr'), ('ww', 'depends_on', 'xx')], **opts)
        #TODO self._test_cant('delete', self.visitor, [('ww', 'links_to', 'wr')], **opts)

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
        self._test_can('search', self.testsysadmin, self.ENTITY_NAME, entity_types=['dataset']) # cannot search groups

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
        self._test_cant('search', self.pkggroupadmin, self.ENTITY_NAME, entity_types=['dataset'])

    def test_site_reader(self):
        self._test_can('search', self.site_reader, self.ENTITY_NAME, entity_types=['dataset']) # cannot search groups
        self._test_can('read', self.site_reader, self.ENTITY_NAME, entity_types=['tag'])

    def test_outcast_search(self):
        self._test_cant('search', self.outcast, self.ENTITY_NAME, entity_types=['dataset']) # cannot search groups
        self._test_cant('read', self.outcast, self.ENTITY_NAME, entity_types=['tag'])

        
class TestLockedDownViaRoles(TestController):
    '''Use case:
           * 'Visitor' has no edit rights
           * 'Reader' role is redefined to not be able to READ (!) or SITE_READ

    '''
    @classmethod
    def setup_class(self):
        model.repo.init_db()
        q = model.Session.query(model.UserObjectRole) \
            .filter(sa.or_(model.UserObjectRole.role==model.Role.EDITOR,
                           model.UserObjectRole.role==model.Role.ANON_EDITOR)) \
            .filter(model.UserObjectRole.user==model.User.by_name(u"visitor"))
        for role in q:
            model.Session.delete(role)
        
        q = model.Session.query(model.RoleAction).filter(model.RoleAction.role==model.Role.READER)
        for role_action in q:
            model.Session.delete(role_action)
        
        model.repo.commit_and_remove()
        setup_test_search_index()
        TestUsage._create_test_data()
        model.Session.remove()
        self.user_name = TestUsage.mrloggedin.name.encode('utf-8')
    
    def _check_logged_in_users_authorized_only(self, offset):
        '''Checks the offset is accessible to logged in users only.'''
        res = self.app.get(offset, extra_environ={})
        assert res.status not in [200], res.status
        res = self.app.get(offset, extra_environ={'REMOTE_USER': self.user_name})
        assert res.status in [200], res.status

    def test_home(self):
        self._check_logged_in_users_authorized_only('/')
    
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
    
    def test_new_package(self):
        offset = url_for(controller='package', action='new')
        self._check_logged_in_users_authorized_only(offset)

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()
        model.Session.remove()
        search.clear()
