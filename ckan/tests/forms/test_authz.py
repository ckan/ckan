import ckan.model as model
import ckan.forms
from ckan.tests import *
import ckan.authz

class DummyContext(object):
    name = u'testuser'
c = DummyContext

class Test(object):
    @classmethod
    def setup_class(self):
        model.Session.remove()
        ckan.tests.CreateTestData.create()
        self.authorizer = ckan.authz.Authorizer()
        model.repo.commit_and_remove()

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()

    def test_1_render_not_authorized(self):
        fs = ckan.forms.authz_fs
        anna = model.Package.by_name(u'annakarenina')
        c.user = u'test'
        fs = fs(c, package=anna) # bind
        out = fs.render()
        assert out
        print out
        for s in ['Editor', 'Admin', 'Anyone', 'logged in', 'annafan']:
            assert s in out, s
        assert '''<span id="authz"><table>
<tr> <th>User</th> <th>Role</th> </tr>''' in out

    def test_1_render_not_authorized_visitor(self):
        fs = ckan.forms.authz_fs
        anna = model.Package.by_name(u'annakarenina')
        c.user = u''
        c.author = u'123.123.123.123'
        fs = fs(c, package=anna) # bind
        out = fs.render()
        assert out
        print out
        for s in ['Editor', 'Admin', 'Anyone', 'logged in', 'annafan']:
            assert s in out, s
        assert '''<span id="authz"><table>
<tr> <th>User</th> <th>Role</th> </tr>''' in out

    def test_1_render_authorized(self):
        fs = ckan.forms.authz_fs
        anna = model.Package.by_name(u'annakarenina')
        c.user = u'annafan'
        fs = fs(c, package=anna) # bind
        out = fs.render()
        assert out
        print out
        for s in ['Reader', 'Editor', 'Admin', 'Anyone', 'logged in', 'annafan']:
            assert s in out, s
        assert '<td>Anyone</td> <td><select id="0-role" name="0-role">' in out

    def test_1_render_authorized_sysadmin(self):
        fs = ckan.forms.authz_fs
        anna = model.Package.by_name(u'annakarenina')
        c.user = u'testsysadmin'
        fs = fs(c, package=anna) # bind
        out = fs.render()
        assert out
        print out
        for s in ['Reader', 'Editor', 'Admin', 'Anyone', 'logged in', 'annafan']:
            assert s in out, s
        assert '<td>Anyone</td> <td><select id="0-role" name="0-role">' in out

    def test_2_sync_update(self):
        anna = model.Package.by_name(u'annakarenina')
        user = model.User.by_name(model.PSEUDO_USER__VISITOR)
        role = model.Role.EDITOR
        assert role in self.authorizer.get_roles(user.name, anna)
        indict = {u'0-role':'None'}
        
        fs = ckan.forms.authz_fs(c, anna, data=indict)
        model.repo.new_revision()
        fs.sync()

        assert role not in self.authorizer.get_roles(user.name, anna)

        model.repo.commit_and_remove()
        

