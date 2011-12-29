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
        model.repo.new_revision()
        group1 = model.Group(name=u'group1', title=u'Test Group',
                             description=u'This is a test group')
        model.Session.add(group1)
        model.repo.commit_and_remove()
        grp = model.Group.by_name(u'group1')
        assert grp.title == u'Test Group'
        assert grp.description == u'This is a test group'
        assert grp.active_packages().all() == []

    def test_2_add_packages(self):
        model.repo.new_revision()
        
        self.russian_group = model.Group(name=u'russian',
                                         title=u'Russian Group',
                             description=u'This is the russian group')
        model.Session.add(self.russian_group)
        anna = model.Package.by_name(u'annakarenina')
        war = model.Package.by_name(u'warandpeace')
        model.Session.add(model.Member(group=self.russian_group,
                                       table_id=anna.id,
                                       table_name='package')
                         )
        model.Session.add(model.Member(group=self.russian_group,
                                       table_id=war.id,
                                       table_name='package')
                         )
        model.repo.commit_and_remove()
        
        grp = model.Group.by_name(u'russian')
        assert grp.title == u'Russian Group'
        anna = model.Package.by_name(u'annakarenina')
        war = model.Package.by_name(u'warandpeace')
        assert set(grp.active_packages().all()) == set((anna, war)), grp.active_packages().all()
        assert grp in anna.get_groups()


class TestGroupRevisions:
    @classmethod
    def setup_class(self):
        model.Session.remove()
        CreateTestData.create()
        self.name = u'revisiontest'

        # create pkg
        self.descriptions = [u'Written by Puccini', u'Written by Rossini', u'Not written at all', u'Written again', u'Written off']
        rev = model.repo.new_revision()
        self.grp = model.Group(name=self.name)
        model.Session.add(self.grp)
        self.grp.description = self.descriptions[0]
        self.grp.extras['mykey'] = self.descriptions[0]
        model.repo.commit_and_remove()

        # edit pkg
        for i in range(5)[1:]:
            rev = model.repo.new_revision()
            grp = model.Group.by_name(self.name)
            grp.description = self.descriptions[i]
            grp.extras['mykey'] = self.descriptions[i]
            model.repo.commit_and_remove()

        self.grp = model.Group.by_name(self.name)        

    @classmethod
    def teardown_class(self):
        #rev = model.repo.new_revision()
        #grp = model.Group.by_name(self.name)
        #grp.purge()
        #model.repo.commit_and_remove()
        model.repo.rebuild_db()

    def test_1_all_revisions(self):
        all_rev = self.grp.all_revisions
        num_descs = len(self.descriptions)
        assert len(all_rev) == num_descs, len(all_rev)
        for i, rev in enumerate(all_rev):
            assert rev.description == self.descriptions[num_descs - i - 1], \
                '%s != %s' % (rev.description, self.descriptions[i])
                
    def test_2_extras(self):
        all_rev = self.grp.all_revisions
        num_descs = len(self.descriptions)
        assert len(all_rev) == num_descs, len(all_rev)
        for i, rev in enumerate(all_rev):
            #print "REVISION", dir(rev)
            #assert rev.extras['mykey'] == self.descriptions[num_descs - i - 1], \
            #    '%s != %s' % (rev.extras['mykey'], self.descriptions[i])
            pass

