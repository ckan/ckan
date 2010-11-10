from nose.plugins.skip import SkipTest

from ckan.tests import *
from ckan.authz import Authorizer
import ckan.model as model
from base import FunctionalTestCase

class TestAuthorizationGroup(FunctionalTestCase):

    @classmethod
    def setup_class(self):
        model.Session.remove()
        CreateTestData.create()
        model.repo.new_revision()
        treasury = model.AuthorizationGroup(name=u'treasury')
        health = model.AuthorizationGroup(name=u'health')
        model.Session.add(treasury)
        model.Session.add(health)
        model.add_user_to_authorization_group(model.User.by_name(u"russianfan"), 
                                              treasury, model.Role.ADMIN)
        model.repo.commit_and_remove()

    @classmethod
    def teardown_class(self):
        model.Session.remove()
        model.repo.rebuild_db()
        model.Session.remove()

    def test_mainmenu(self):
        offset = url_for(controller='home', action='index')
        res = self.app.get(offset)
        assert 'Authorization Groups' in res, res
        assert 'Authorization Groups</a>' in res, res
        res = res.click(href='/authorizationgroup')
        assert '<h2>Authorization Groups</h2>' in res, res

    def test_index(self):
        offset = url_for(controller='authorizationgroup')
        res = self.app.get(offset, extra_environ={'REMOTE_USER': 'russianfan'})
        assert '<h2>Authorization Groups</h2>' in res, res
        group_count = Authorizer.authorized_query(u'russianfan', model.AuthorizationGroup).count()
        assert 'There are %s authorization groups.' % group_count in self.strip_tags(res), res
        authz_groupname = u'treasury'
        authz_group = model.AuthorizationGroup.by_name(unicode(authz_groupname))
        group_users_count = len(authz_group.users)
        self.check_named_element(res, 'tr', authz_groupname, group_users_count)
        #res = res.click(authz_groupname)
        #assert authz_groupname in res, res
        
    def test_read(self):
        name = u'treasury'
        offset = url_for(controller='authorization_group', action='read', id=name)
        res = self.app.get(offset, extra_environ={'REMOTE_USER': 'russianfan'})
        main_res = self.main_div(res)
        assert '%s - Authorization Groups' % name in res, res
        #assert 'edit' in main_res, main_res
        assert name in res, res

    def test_new(self):
        offset = url_for(controller='authorization_group')
        res = self.app.get(offset, extra_environ={'REMOTE_USER': 'russianfan'})
        assert 'Create a new authorization group' in res, res
        

class TestEdit(TestController):
    groupname = u'treasury'

    @classmethod
    def setup_class(self):
        model.Session.remove()
        CreateTestData.create()
        model.repo.new_revision()
        treasury = model.AuthorizationGroup(name=u'treasury')
        health = model.AuthorizationGroup(name=u'health')
        model.Session.add(treasury)
        model.Session.add(health)
        model.add_user_to_authorization_group(model.User.by_name(u"russianfan"), 
                                              treasury, model.Role.ADMIN)
        model.repo.commit_and_remove()
        
        self.username = u'testusr'
        model.repo.new_revision()
        model.Session.add(model.User(name=self.username))
        model.repo.commit_and_remove()

    @classmethod
    def teardown_class(self):
        model.Session.remove()
        model.repo.rebuild_db()
        model.Session.remove()

    def test_0_not_authz(self):
        offset = url_for(controller='authorization_group', action='edit', id=self.groupname)
        # 401 gets caught by repoze.who and turned into redirect
        res = self.app.get(offset, status=[302, 401])
        res = res.follow()
        assert res.request.url.startswith('/user/login')

    def test_1_read_allowed_for_admin(self):
        raise SkipTest()
        offset = url_for(controller='authorization_group', action='edit', id=self.groupname)
        res = self.app.get(offset, status=200, extra_environ={'REMOTE_USER': 'russianfan'})
        assert 'Edit Authorization Group: %s' % self.groupname in res, res
        
    def test_2_edit(self):
        raise SkipTest()
        offset = url_for(controller='authorization_group', action='edit', id=self.groupname)
        res = self.app.get(offset, status=200, extra_environ={'REMOTE_USER': 'russianfan'})
        assert 'Edit Authorization Group: %s' % self.groupname in res, res

        form = res.forms['group-edit']
        group = model.AuthorizationGroup.by_name(self.groupname)
        usr = model.User.by_name(self.username)
        form['AuthorizationGroupUser--user_name'] = usr.name
        
        res = form.submit('save', status=302, extra_environ={'REMOTE_USER': 'russianfan'})
        # should be read page
        # assert 'Groups - %s' % self.groupname in res, res
        
        model.Session.remove()
        group = model.AuthorizationGroup.by_name(self.groupname)
        
        # now look at packages
        assert len(group.users) == 2
