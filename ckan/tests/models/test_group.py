import ckan.model as model
from ckan.tests import *

class TestGroup(object):

    @classmethod
    def setup_class(self):
        CreateTestData.create()
        model.Session.remove()

    @classmethod
    def teardown_class(self):
        model.Session.remove()
        model.repo.rebuild_db()
        model.Session.remove()

    def test_1_basic(self):
        group1 = model.Group(name=u'group1', title=u'Test Group',
                             description=u'This is a test group')
        model.Session.add(group1)
        model.repo.commit_and_remove()
        grp = model.Group.by_name(u'group1')
        assert grp.title == u'Test Group'
        assert grp.description == u'This is a test group'
        assert grp.packages == []

    def test_2_add_packages(self):
        self.russian_group = model.Group(name=u'russian',
                                         title=u'Russian Group',
                             description=u'This is the russian group')
        model.Session.add(self.russian_group)
        anna = model.Package.by_name(u'annakarenina')
        war = model.Package.by_name(u'warandpeace')
        self.russian_group.packages = [anna, war]
        model.repo.commit_and_remove()
        
        grp = model.Group.by_name(u'russian')
        assert grp.title == u'Russian Group'
        anna = model.Package.by_name(u'annakarenina')
        war = model.Package.by_name(u'warandpeace')
        assert grp.packages == [anna, war], grp.packages
        assert grp in anna.groups

