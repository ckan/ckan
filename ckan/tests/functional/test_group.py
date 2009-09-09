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
        assert name in res
        res = res.click(pkgname)
        assert 'Packages - %s' % pkgname in res
