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

        # now testsysadmin goes and looks at the page for anauthzgroup, he should see that it has no members
        anauthzgroup_url = url_for(controller='authorizationgroup', action='anauthzgroup')
        res = self.app.get(anauthzgroup_url, status=200, extra_environ={'REMOTE_USER': 'testsysadmin'})
        assert 'There are 0 users in this' in res, 'testsysadmin should see the page, there should be no users in the group'

        # now testsysadmin adds annafan to anauthzgroup via the edit page
        anauthzgroup_edit_url = url_for(controller='authorizationgroup', action='edit', id='anauthzgroup')
        res = self.app.get(anauthzgroup_edit_url, status=200, extra_environ={'REMOTE_USER': 'testsysadmin'})
        group_edit_form = res.forms['group-edit']
        user_field = group_edit_form.fields['AuthorizationGroupUser--user_name'][0]
        user_field.value = u'annafan'
        submit_res = group_edit_form.submit('save',extra_environ={'REMOTE_USER': 'testsysadmin'})

        # anauthzgroup should now have one member, annafan, and she should be a reader on the group
        anauthzgroup_users=[x.name for x in model.AuthorizationGroup.by_name('anauthzgroup').users]
        assert anauthzgroup_users==[u'annafan'], 'anauthzgroup should contain annafan (only)'

        # she should be the only user who is a reader
        anauthzgroup_user_roles = [(x.user.name, x.role) for x in model.AuthorizationGroup.by_name('anauthzgroup').roles if x.user]
        assert anauthzgroup_user_roles == [(u'annafan', u'reader')], 'annafan should be a reader'

        # and anotherauthzgroup should be the only authzgroup with a role, which should be 'editor'
        anauthzgroup_authzgroup_roles = [(x.authorized_group.name, x.role) for x in model.AuthorizationGroup.by_name('anauthzgroup').roles if x.authorized_group]

        assert anauthzgroup_authzgroup_roles == [(u'anotherauthzgroup', u'editor')]

        # annafan should now be able to see both the groups, since she is a
        # reader on and a member of anauthzgroup, which group is an admin on
        # anotherauthzgroup
        res = self.app.get(auth_group_index_url, status=200, 
                           extra_environ={'REMOTE_USER': 'annafan'})

        assert 'There are <strong>2</strong> auth' in res, \
                                  "annafan should now be able to see both groups"

        # If she goes to the page for anauthzgroup then she should see the list of users (just her)
        anauthzgroup_url = url_for(controller='authorizationgroup', action='anauthzgroup')
        res = self.app.get(anauthzgroup_url, status=200, extra_environ={'REMOTE_USER': 'annafan'})
        assert 'There are 1 users in this' in res, 'annafan should be able to see the list of members'
        assert 'annafan' in res, 'annafan should be listed as a member'

        # but she shouldn't be able to see the edit page for that group.  the
        # behaviour here is a bit weird, since in the browser she gets
        # redirected to the login page, but from these tests, she just gets a
        # 401, with no apparent redirect.
        anauthzgroup_edit_url = url_for(controller='authorizationgroup', action='edit', id='anauthzgroup')
        res = self.app.get(anauthzgroup_edit_url, status=401, extra_environ={'REMOTE_USER': 'annafan'})
        assert 'not authorized to edit' in res, 'annafan should not be able to edit the list of members'
        # that means that we get a flash message left over for the next page
  
        # I'm going to assert that behaviour here, just to note it. It's most
        # definitely not required functionality!  We'll do a dummy fetch of the
        # main page for anauthzgroup, which will have the errant flash message
        res = self.app.get(anauthzgroup_url,extra_environ={'REMOTE_USER': 'annafan'})
        assert 'not authorized to edit' in res, 'flash message should carry over to next fetch'
        # But if we do the dummy fetch twice, the flash message should have gone
        res = self.app.get(anauthzgroup_url,extra_environ={'REMOTE_USER': 'annafan'})
        assert 'not authorized to edit' not in res, 'flash message should have gone'

        # however she should be able to see the edit page for anotherauthzgroup, since she's an admin
        # on it by virtue of being a member of anauthzgroup
        anotherauthzgroup_edit_url = url_for(controller='authorizationgroup', action='edit', id='anotherauthzgroup')
        res = self.app.get(anotherauthzgroup_edit_url, status=200, extra_environ={'REMOTE_USER': 'annafan'})
        # for reasons of complete paranoia, check that the flash message hasn't carried over into this page
        assert 'not authorized to edit' not in res, 'flash message should not be there!, what on earth...'
        assert 'There are no users' in res, "shouldn't be any users in this group"

        # That means that she can change the name of the group
        # note that she could change the name of to anauthzgroup, which causes problems.
        # We'll change it to something less vexing.
        import re
        p = re.compile('AuthorizationGroup-.*-name')
        groupnamebox = [ v for k,v in res.forms['group-edit'].fields.items() if p.match(k)][0][0]
        groupnamebox.value = 'annasauthzgroup'
        res = res.forms['group-edit'].submit('save').follow()
        

        ## BUG HERE: PAGE DOES NOT GET RENAMED. (HOWEVER IT DOES SEEM TO FROM BROWSER)

        # annafan should be able to see the admin page of the newly renamed
        # group by virtue of being a member of anauthzgroup
        annasauthzgroup_authz_url = url_for(controller='authorizationgroup', action='authz', id='annasauthzgroup')
        res = self.app.get(annasauthzgroup_authz_url, status=404, extra_environ={'REMOTE_USER': 'annafan'})

        # Let's try the old address for that
        annasauthzgroup_authz_url = url_for(controller='authorizationgroup', action='authz', id='anotherauthzgroup')
        res = self.app.get(annasauthzgroup_authz_url, status=200, extra_environ={'REMOTE_USER': 'annafan'})

        # So she can remove anauthzgroup's admin role on her group
        # The button to remove that role is a link, rather than a submit
        # I assume there is a better way to do this than searching by regex, but I can't find it
        import re
        delete_links = re.compile('<a href="(.*)" title="delete">').findall(res.body)
        assert len(delete_links) == 1, "There should only be one delete link here"
        delete_link = delete_links[0]

        # Paranoid check, try to follow link without credentials. Should be redirected.
        res = self.app.get(delete_link, status=302)
        res = res.follow()
        assert 'Not authorized to edit authorization for group' in res,\
                  "following link without credentials should result in redirection to login page"


        # Now follow it as annafan, which should work.
        res = self.app.get(delete_link, status=200, extra_environ={'REMOTE_USER': 'annafan'})
        assert "Deleted role 'admin' for authorization group 'anauthzgroup'" in res,\
                                                     "Page should mention the deleted role"
        
        # Trying it a second time should fail since she's now not an admin.
        res = self.app.get(delete_link, status=401, extra_environ={'REMOTE_USER': 'annafan'})

        # No one should now have any rights on annasauthzgroup, including annafan herself.
        # So this should fail too. Again, get a 401 error here, but in the browser we get redirected if we try.
        res = self.app.get(annasauthzgroup_authz_url, status=401, extra_environ={'REMOTE_USER': 'annafan'})

        # testsysadmin can put her back. 
        # It appears that the select boxes on this form need to be set by id
        anauthzgroupid = model.AuthorizationGroup.by_name(u'anauthzgroup').id
        annafanid = model.User.by_name(u'annafan').id

        # first try to make both anauthzgroup and annafan editors. This should fail.
        res = self.app.get(annasauthzgroup_authz_url, status=200, extra_environ={'REMOTE_USER': 'testsysadmin'})
        gaf= res.forms['group-authz']
        gaf['AuthorizationGroupRole--authorized_group_id'] = anauthzgroupid
        gaf['AuthorizationGroupRole--role'] = 'editor'
        gaf['AuthorizationGroupRole--user_id'] = annafanid
        res = gaf.submit('save', status=200, extra_environ={'REMOTE_USER': 'testsysadmin'})
        assert 'Please select either a user or an authorization group, not both.' in res,\
             'request should fail if you change both user and authz group'

        # settle for just anauthzgroup
        res = self.app.get(annasauthzgroup_authz_url, status=200, extra_environ={'REMOTE_USER': 'testsysadmin'})
        gaf= res.forms['group-authz']
        gaf['AuthorizationGroupRole--authorized_group_id'] = anauthzgroupid
        gaf['AuthorizationGroupRole--role'] = 'editor'
        res = gaf.submit('save',status=200, extra_environ={'REMOTE_USER': 'testsysadmin'})
        assert "Added role 'editor' for authorization group 'anauthzgroup'" in res, "no flash message"

        # and make annafan a reader 
        res = self.app.get(annasauthzgroup_authz_url, status=200, extra_environ={'REMOTE_USER': 'testsysadmin'})
        gaf= res.forms['group-authz']
        gaf['AuthorizationGroupRole--user_id'] = annafanid
        gaf['AuthorizationGroupRole--role'] = 'reader'
        res = gaf.submit('save', status=200, extra_environ={'REMOTE_USER': 'testsysadmin'})
        assert "Added role 'reader' for user 'annafan'" in res, "no flash message"

        # annafan should now be able to add her friends to annasauthzgroup
        annasauthzgroup_edit_url = url_for(controller='authorizationgroup', action='edit', id='anotherauthzgroup')
        res = self.app.get(anotherauthzgroup_edit_url, status=200, extra_environ={'REMOTE_USER': 'annafan'})
        res.forms['group-edit']['AuthorizationGroupUser--user_name']='tester'
        # this follows the post/redirect/get pattern
        res = res.forms['group-edit'].submit('save', status=302, extra_environ={'REMOTE_USER': 'annafan'})
        res = res.follow(status=200, extra_environ={'REMOTE_USER': 'annafan'})
        #she gets redirected to the group view page
        assert 'tester' in res, 'tester not added?'
 
        # she needs to do them one by one
        res = self.app.get(anotherauthzgroup_edit_url, status=200, extra_environ={'REMOTE_USER': 'annafan'})
        assert 'tester' in res, 'tester not in edit form'
        res.forms['group-edit']['AuthorizationGroupUser--user_name']='russianfan'        
        res = res.forms['group-edit'].submit('save', status=302, extra_environ={'REMOTE_USER': 'annafan'})
        res = res.follow(status=200, extra_environ={'REMOTE_USER': 'annafan'})
        
        # and finally adds herself
        res = self.app.get(anotherauthzgroup_edit_url, status=200, extra_environ={'REMOTE_USER': 'annafan'})
        assert 'russianfan' in res, 'russianfan not added?'
        res.forms['group-edit']['AuthorizationGroupUser--user_name']='annafan'        
        res = res.forms['group-edit'].submit('save', status=302, extra_environ={'REMOTE_USER': 'annafan'})
        res = res.follow(status=200, extra_environ={'REMOTE_USER': 'annafan'})
        assert 'annafan' in res, 'annafan not added?'

        # finally let's check that annafan can create an authzgroup
        new_authzgroup_url = url_for(controller='authorizationgroup', action='new', id="")
        # I think our url is wrong for some reason because we get redirected
        res = self.app.get(new_authzgroup_url, status=301, extra_environ={'REMOTE_USER': 'annafan'})
        res = res.follow(status=200, extra_environ={'REMOTE_USER': 'annafan'})
        assert 'New Authorization Group' in res, "wrong page"

        gef = res.forms['group-edit']
        gef['AuthorizationGroup--name']="newgroup"
        gef['AuthorizationGroupUser--user_name'] = "russianfan"
        res = gef.submit('save', status=302, extra_environ={'REMOTE_USER': 'annafan'})
        #post/redirect/get
        res = res.follow(status=200, extra_environ={'REMOTE_USER': 'annafan'})
        
        assert 'newgroup'   in res, "should have redirected to the newgroup page"
        assert 'russianfan' in res, "no russianfan"
        assert 'There are 1 users in this authorization group' in res, "missing text"

