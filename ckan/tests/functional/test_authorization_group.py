from nose.plugins.skip import SkipTest

from ckan.tests import *
from ckan.authz import Authorizer
import ckan.model as model
from base import FunctionalTestCase
from ckan.tests import search_related

class TestAuthorizationGroup(FunctionalTestCase):

    @classmethod
    def setup_class(self):
        model.Session.remove()
        model.repo.init_db()
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

    @search_related
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


class TestAuthorizationGroupWalkthrough(FunctionalTestCase):

    @classmethod
    def setup_class(self):
        model.Session.remove()
        model.repo.init_db()
        CreateTestData.create()
        model.repo.commit_and_remove()

    @classmethod
    def teardown_class(self):
        model.Session.remove()
        model.repo.rebuild_db()
        model.Session.remove()

    def authzgroups_walkthrough(self):
        # log in as annafan, look at authorization groups page, 
        # (http://localhost:5000/authorizationgroup), there should be 0 groups
        # (two groups actually exist in the default test data, but annafan has read permission
        # on neither)
        auth_group_index_url = url_for(controller='authorization_group', action='index')

        # look as annafan
        res = self.app.get(auth_group_index_url, status=200, 
                           extra_environ={'REMOTE_USER': 'annafan'})

        assert 'There are <strong>0</strong> auth' in res, \
                                  "Should lie to annafan about number of groups"

        # look as testsysadmin, who should be able to see the two groups in the test data
        res = self.app.get(auth_group_index_url, status=200, 
                                        extra_environ={'REMOTE_USER': 'testsysadmin'})
        assert 'There are <strong>2</strong> auth' in res, "Should be accurate for testsysadmin"

        anauthzgroup_url = url_for(controller='authorizationgroup', action='anauthzgroup')
        res = self.app.get(anauthzgroup_url, status=200, extra_environ={'REMOTE_USER': 'testsysadmin'})
        assert 'There are 0 users in this' in res, 'testsysadmin should see the page, there should be no users in the group'

        # now testsysadmin adds annafan to anauthzgroup
        anauthzgroup_edit_url = url_for(controller='authorizationgroup', action='edit', id='anauthzgroup')
        res = self.app.get(anauthzgroup_edit_url, status=200, extra_environ={'REMOTE_USER': 'testsysadmin'})
        group_edit_form = res.forms['group-edit']
        user_field = group_edit_form.fields['AuthorizationGroupUser--user_name'][0]
        user_field.value = u'annafan'
        submit_res = group_edit_form.submit('save',extra_environ={'REMOTE_USER': 'testsysadmin'})

        # anauthzgroup should now have one member, annafan, and she should be a reader on the group
        anauthzgroup_users=[x.name for x in model.AuthorizationGroup.by_name('anauthzgroup').users]
        assert anauthzgroup_users==[u'annafan'], 'anauthzgroup should contain annafan (only)'


        # if we've got this far, drop into the debugger

        import re
        s = re.compile('There are.*auth').findall(res.body)
        print s

        import pdb
        pdb.set_trace()


  

        # anauthzgroup is an admin for anotherauthzgroup, so she has control over it.
        # Now go and look at the groups http://localhost:5000/authorizationgroup as annafan  
        # She should be able to see both groups
        # If she goes to anauthzgroup http://localhost:5000/authorizationgroup/anauthzgroup then she should see the list of users (her)
        # If she goes to anotherauthzgroup  http://localhost:5000/authorizationgroup/anotherauthzgroup then she should be able to see the admin page
        # She can downgrade anauthzgroup to only be an editor on anotherauthzgroup
        # This should lock her out of the page, surely? But it doesn't. 
        # The admin tab goes, but she is still seeing the form. However if she tries to put it back then she's redirected.
        # She can't see the admin page anymore, but she should still be able to edit the userlist for the group.
        # She adds tester, russianfan, and herself, necessitating three separate visits to the edit page.
        # Why in the search box doesn't searcing for 'Wonderful' find 'A Wonderful Story'? Create ticket for this.
        # She goes to A Wonderful Story, which it appears she's an admin on, because visitor is!
        # And adds anotherauthzgroup as admin on A Wonderful Story, and removes all other entries.
        # She should be able to see the authz page, as should testsysadmin and tester
        # She goes to anotherauthzgroup, and removes tester. Tester should no longer be able to see that A Wonderful Story even exists
        # http://localhost:5000/package/authz/warandpeace
        # She puts him back in, and he should be able to see the authz page again. 



        import pdb
        pdb.set_trace()
        assert False, "deliberate fail"