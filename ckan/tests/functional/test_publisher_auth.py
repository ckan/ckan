import re

from nose.tools import assert_equal

import ckan.model as model
from ckan.lib.create_test_data import CreateTestData
from ckan.logic import NotAuthorized
        

from ckan.tests import *
from ckan.tests import setup_test_search_index
from base import FunctionalTestCase
from ckan.tests import search_related, is_search_supported

        
class TestPublisherGroups(FunctionalTestCase):

    @classmethod
    def setup_class(self):                        
        from ckan.tests.mock_publisher_auth import MockPublisherAuth
        self.auth = MockPublisherAuth()

        model.Session.remove()
        CreateTestData.create(auth_profile='publisher')
        self.groupname = u'david'
        self.deleted_group_name = u'roger'
        self.packagename = u'testpkg'
        model.repo.new_revision()
        model.Group.by_name(u'roger').delete()
        model.Session.add(model.Package(name=self.packagename))
        model.repo.commit_and_remove()

    @classmethod
    def teardown_class(self):
        model.Session.remove()
        model.repo.rebuild_db()
        model.Session.remove()

    def _run_fail_test( self, username, action, group_name=None):
        grp = model.Group.by_name(group_name or self.groupname)   
        context = { 'group': grp, 'model': model, 'user': username }
        try:
            self.auth.check_access(action,context, {})
            assert False, "The user should not have access"
        except NotAuthorized, e:
            pass
    
    def _run_success_test( self, username, action, group_name=None):
        userobj = model.User.get(username)
        grp = model.Group.by_name(group_name or self.groupname)        
        f = model.User.get_groups
        def gg(*args, **kwargs):
            return [grp]
        model.User.get_groups = gg
    
        context = { 'group': grp, 'model': model, 'user': username }
        try:
            self.auth.check_access(action, context, {})
        except NotAuthorized, e:
            assert False, "The user should have %s access: %r." % (action, e.extra_msg)
        model.User.get_groups = f
        
    def test_new_success(self):
        self._run_success_test( 'russianfan', 'group_create' )
        
    def test_new_fail(self):
        self._run_fail_test( 'russianfan', 'group_create' )

    def test_new_anon_fail(self):
        self._run_fail_test( '', 'group_create' )

    def test_new_unknown_fail(self):
        self._run_fail_test( 'nosuchuser', 'group_create' )
    
    def test_edit_success(self):
        """ Success because user in group """
        self._run_success_test( 'russianfan', 'group_update' )
        
    def test_edit_fail(self):
        """ Fail because user not in group """
        self._run_fail_test( 'russianfan', 'group_update' )
        
    def test_edit_anon_fail(self):
        """ Fail because user is anon """
        self._run_fail_test( '', 'group_update' )

    def test_edit_unknown_fail(self):
        self._run_fail_test( 'nosuchuser', 'group_update' )

    def test_delete_success(self):
        """ Success because user in group """
        self._run_success_test( 'russianfan', 'group_delete' )
        
    def test_delete_fail(self):
        """ Fail because user not in group """
        self._run_fail_test( 'russianfan', 'group_delete' )
        
    def test_delete_anon_fail(self):
        """ Fail because user is anon """
        self._run_fail_test( '', 'group_delete' )

    def test_delete_unknown_fail(self):
        self._run_fail_test( 'nosuchuser', 'group_delete' )
        
    def test_read_deleted_success(self):
        """ Success because user in group """
        self._run_success_test('testsysadmin', 'group_show',
                               group_name=self.deleted_group_name)
        
    def test_read_deleted_fail(self):
        """ Fail because user not in group """
        self._run_fail_test('annafan', 'group_show',
                            group_name=self.deleted_group_name)

class TestPublisherShow(FunctionalTestCase):
    
    @classmethod
    def setup_class(self):                        
        from ckan.tests.mock_publisher_auth import MockPublisherAuth
        self.auth = MockPublisherAuth()

        model.Session.remove()
        CreateTestData.create(auth_profile='publisher')
        self.groupname = u'david'
        self.packagename = u'testpkg'
        model.repo.new_revision()
        model.Session.add(model.Package(name=self.packagename))
        model.repo.commit_and_remove()

    @classmethod
    def teardown_class(self):
        model.Session.remove()
        model.repo.rebuild_db()
        model.Session.remove()

    def test_package_show_deleted_success(self):
        userobj = model.User.get('russianfan')
        grp = model.Group.by_name(self.groupname)     
        pkg = model.Package.by_name(self.packagename)
        pkg.state = 'deleted'
        
        f = model.User.get_groups
        g = model.Package.get_groups
        def gg(*args, **kwargs):
            return [grp]
        model.User.get_groups = gg
        model.Package.get_groups = gg
        
        context = { 'package': pkg, 'model': model, 'user': userobj.name }
        try:
            self.auth.check_access('package_show', context, {})
        except NotAuthorized, e:
            assert False, "The user should have %s access: %r." % (action, e.extra_msg)
        model.User.get_groups = f
        model.Package.get_groups = g
        pkg.state = "active"

    def test_package_show_normal_success(self):
        userobj = model.User.get('russianfan')
        grp = model.Group.by_name(self.groupname)     
        pkg = model.Package.by_name(self.packagename)
        pkg.state = "active"
        
        context = { 'package': pkg, 'model': model, 'user': userobj.name }
        try:
            self.auth.check_access('package_show', context, {})
        except NotAuthorized, e:
            assert False, "The user should have %s access: %r." % ("package_show", e.extra_msg)
        
    def test_package_show_deleted_fail(self):
        userobj = model.User.get('russianfan')
        grp = model.Group.by_name(self.groupname)     
        pkg = model.Package.by_name(self.packagename)
        pkg.state = 'deleted'
        
        g = model.Package.get_groups
        def gg(*args, **kwargs):
            return [grp]
        model.Package.get_groups = gg
        
        context = { 'package': pkg, 'model': model, 'user': userobj.name }
        try:
            self.auth.check_access('package_show', context, {})
            assert False, "The user should not have access."            
        except NotAuthorized, e:
            pass
        model.Package.get_groups = g
        pkg.state = "active"
        


class TestPublisherGroupPackages(FunctionalTestCase):

    @classmethod
    def setup_class(self):                        
        from ckan.tests.mock_publisher_auth import MockPublisherAuth
        self.auth = MockPublisherAuth()

        model.Session.remove()
        CreateTestData.create(auth_profile='publisher')
        self.groupname = u'david'
        self.packagename = u'testpkg'
        model.repo.new_revision()
        model.Session.add(model.Package(name=self.packagename))
        model.repo.commit_and_remove()

    @classmethod
    def teardown_class(self):
        model.Session.remove()
        model.repo.rebuild_db()
        model.Session.remove()

    def _run_fail_test( self, username, action):
        pkg = model.Package.by_name(self.packagename)
        context = { 'package': pkg, 'model': model, 'user': username }
        try:
            self.auth.check_access(action, context, {})
            assert False, "The user should not have access"
        except NotAuthorized, e:
            pass
    
    def _run_success_test( self, username, action):    
        userobj = model.User.get(username)
        grp = model.Group.by_name(self.groupname)     
        pkg = model.Package.by_name(self.packagename)
        
        f = model.User.get_groups
        g = model.Package.get_groups
        def gg(*args, **kwargs):
            return [grp]
        model.User.get_groups = gg
        model.Package.get_groups = gg
        
        context = { 'package': pkg, 'model': model, 'user': username }
        try:
            self.auth.check_access(action, context, {})
        except NotAuthorized, e:
            assert False, "The user should have %s access: %r." % (action, e.extra_msg)
        model.User.get_groups = f
        model.Package.get_groups = g
        
    def test_new_success(self):
        self._run_success_test( 'russianfan', 'package_create' )
     
    # Currently valid to have any logged in user succeed    
    #def test_new_fail(self):
    #    self._run_fail_test( 'russianfan', 'package_create' )

    def test_new_anon_fail(self):
        self._run_fail_test( '', 'package_create' )

    def test_new_unknown_fail(self):
        self._run_fail_test( 'nosuchuser', 'package_create' )
    
    def test_edit_success(self):
        """ Success because user in group """
        self._run_success_test( 'russianfan', 'package_update' )
        
    def test_edit_fail(self):
        """ Fail because user not in group """
        self._run_fail_test( 'russianfan', 'package_update' )
        
    def test_edit_anon_fail(self):
        """ Fail because user is anon """
        self._run_fail_test( '', 'package_update' )

    def test_edit_unknown_fail(self):
        self._run_fail_test( 'nosuchuser', 'package_update' )

    def test_delete_success(self):
        """ Success because user in group """
        self._run_success_test( 'russianfan', 'package_delete' )
        
    def test_delete_fail(self):
        """ Fail because user not in group """
        self._run_fail_test( 'russianfan', 'package_delete' )
        
    def test_delete_anon_fail(self):
        """ Fail because user is anon """
        self._run_fail_test( '', 'package_delete' )

    def test_delete_unknown_fail(self):
        self._run_fail_test( 'nosuchuser', 'package_delete' )
        

class TestPublisherPackageRelationships(FunctionalTestCase):

    @classmethod
    def setup_class(self):                        
        from ckan.tests.mock_publisher_auth import MockPublisherAuth
        self.auth = MockPublisherAuth()

        model.Session.remove()
        CreateTestData.create(auth_profile='publisher')
        self.groupname = u'david'
        self.package1name = u'testpkg'
        self.package2name = u'testpkg2'
        model.repo.new_revision()
        pkg1 = model.Package(name=self.package1name)
        pkg2 = model.Package(name=self.package2name)
        model.Session.add( pkg1 )
        model.Session.add( pkg2 )  
        model.Session.flush()
        pkg1 = model.Package.by_name(self.package1name)
        pkg2 = model.Package.by_name(self.package2name)        

        self.rel = model.PackageRelationship(name="test", type='depends_on')
        self.rel.subject = pkg1
        self.rel.object = pkg2
        model.Session.add( self.rel )
        model.repo.commit_and_remove()

    @classmethod
    def teardown_class(self):
        model.Session.remove()
        model.repo.rebuild_db()
        model.Session.remove()

    def test_create_fail_user( self):
        p1 = model.Package.by_name( self.package1name )
        p2 = model.Package.by_name( self.package2name )        
        
        context = { 'model': model, 'user': 'russianfan' }
        try:
            self.auth.check_access('package_relationship_create', context, {'id': p1.id, 'id2': p2.id})
            assert False, "The user should not have access."            
        except NotAuthorized, e:
            pass
    
    def test_create_fail_ddict( self):
        p1 = model.Package.by_name( self.package1name )
        p2 = model.Package.by_name( self.package2name )        
        
        context = { 'model': model, 'user': 'russianfan' }
        try:
            self.auth.check_access('package_relationship_create', context, {'id': p1.id})
            assert False, "The user should not have access."            
        except NotAuthorized, e:
            pass
            
        try:
            self.auth.check_access('package_relationship_create', context, {'id2': p2.id})
            assert False, "The user should not have access."            
        except NotAuthorized, e:
            pass            
                
    def test_create_success(self):
        userobj = model.User.get('russianfan')     

        f = model.User.get_groups
        g = model.Package.get_groups
        def gg(*args, **kwargs):
            return ['test_group']
        model.User.get_groups = gg
        model.Package.get_groups = gg
    
        p1 = model.Package.by_name( self.package1name )
        p2 = model.Package.by_name( self.package2name )        
        
        context = { 'model': model, 'user': 'russianfan' }
        try:
            self.auth.check_access('package_relationship_create', context, {'id': p1.id, 'id2': p2.id})
        except NotAuthorized, e:
            assert False, "The user should have %s access: %r." % (action, e.extra_msg)
        model.User.get_groups = f
        model.Package.get_groups = g

    def test_delete_success(self):
        userobj = model.User.get('russianfan')     

        f = model.User.get_groups
        g = model.Package.get_groups
        def gg(*args, **kwargs):
            return ['test_group']
        model.User.get_groups = gg
        model.Package.get_groups = gg
        
        p1 = model.Package.by_name( self.package1name )
        p2 = model.Package.by_name( self.package2name )    
                
        context = { 'model': model, 'user': 'russianfan', 'relationship': self.rel }
        try:
            self.auth.check_access('package_relationship_delete', context, {'id': p1.id, 'id2': p2.id })
        except NotAuthorized, e:
            assert False, "The user should have %s access: %r." % ('package_relationship_delete', e.extra_msg)            
            
        model.User.get_groups = f
        model.Package.get_groups = g
        

