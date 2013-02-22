from nose.tools import assert_equal

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
        assert grp.packages() == []

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
        assert set(grp.packages()) == set((anna, war)), grp.packages()
        assert grp in anna.get_groups()

    def test_3_search(self):
        model.repo.new_revision()
        model.Session.add(model.Group(name=u'test_org',
                                       title=u'Test org',
                                       type=u'organization'
                         ))
        model.repo.commit_and_remove()


        assert_equal(self._search_results('random'), set([]))
        assert_equal(self._search_results('david'), set(['david']))
        assert_equal(self._search_results('roger'), set(['roger']))
        assert_equal(self._search_results('roger '), set(['roger']))
        assert_equal(self._search_results('David'), set(['david']))
        assert_equal(self._search_results('Dave'), set(['david']))
        assert_equal(self._search_results('Dave\'s'), set(['david']))
        assert_equal(self._search_results('Dave\'s books'), set(['david']))
        assert_equal(self._search_results('Books'), set(['david', 'roger']))
        assert_equal(self._search_results('Books', is_org=True), set([]))
        assert_equal(self._search_results('Test', is_org=True), set(['test_org']))

    def test_search_by_name_or_title_only_returns_active_groups(self):
        model.repo.new_revision()

        active_group = model.Group(name=u'active_group')
        active_group.state = u'active'
        inactive_group = model.Group(name=u'inactive_group')
        inactive_group.state = u'inactive'
        model.Session.add(active_group)
        model.Session.add(inactive_group)
        model.repo.commit_and_remove()

        assert_equal(self._search_results('active_group'), set(['active_group']))
        assert_equal(self._search_results('inactive_group'), set([]))

    def _search_results(self, query, is_org=False):
        results = model.Group.search_by_name_or_title(query,is_org=is_org)
        return set([group.name for group in results])

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

