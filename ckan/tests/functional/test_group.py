from ckan.tests import *
import ckan.model as model

class TestGroup(TestController2):

    @classmethod
    def setup_class(self):
        model.Session.remove()
        CreateTestData.create()

    @classmethod
    def teardown_class(self):
        CreateTestData.delete()

    def test_mainmenu(self):
        offset = url_for(controller='home', action='index')
        res = self.app.get(offset)
        assert 'Groups' in res, res        

    def test_index(self):
        offset = url_for(controller='group')
        res = self.app.get(offset)
        assert 'Groups - List' in res, res
        # rest is same as list

    def test_list(self):
        offset = url_for(controller='group', action='list')
        res = self.app.get(offset)
        print str(res)
        assert 'Groups - List' in res
        group_count = model.Group.query().count()
        assert 'There are %s groups.' % group_count in res
        groupname = 'david'
        assert groupname in res
        res = res.click(groupname)
        assert groupname in res
        
    def test_read(self):
        name = u'david'
        pkgname = u'warandpeace'
        offset = url_for(controller='group', action='read', id=name)
        res = self.app.get(offset)
        assert 'Groups - %s' % name in res
        assert '[edit]' not in res
        assert name in res
        res = res.click(pkgname)
        assert 'Packages - %s' % pkgname in res

    def test_read_and_authorized_to_edit(self):
        name = u'david'
        pkgname = u'warandpeace'
        offset = url_for(controller='group', action='read', id=name)
        res = self.app.get(offset, extra_environ={'REMOTE_USER': 'russianfan'})
        assert 'Groups - %s' % name in res, res
        assert '[edit]' in res
        assert name in res

class TestEdit(TestController2):
    @classmethod
    def setup_class(self):
        model.Session.remove()
        CreateTestData.create()

    @classmethod
    def teardown_class(self):
        model.Session.remove()
        model.repo.rebuild_db()
        model.Session.remove()

    def test_0_not_authz(self):
        groupname = u'david'
        offset = url_for(controller='group', action='edit', id=groupname)
        res = self.app.get(offset, status=[302, 401])
        res = res.follow()
        assert res.request.url.startswith('/user/login')

    def test_1_authz(self):
        groupname = u'david'
        offset = url_for(controller='group', action='edit', id=groupname)
        res = self.app.get(offset, status=200, extra_environ={'REMOTE_USER': 'russianfan'})
        assert 'Edit Group: %s' % groupname in res, res
        
    
