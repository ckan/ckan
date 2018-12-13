# encoding: utf-8

from ckan.tests.legacy import *
import ckan.model as model
from ckan.lib.create_test_data import CreateTestData

class TestCreation:
    @classmethod
    def teardown(self):
        model.repo.rebuild_db()

    def test_normal_creation(self):
        create = CreateTestData
        create.create_arbitrary([{'name':u'the-parent', 'title':u'The Parent'},
                                 {'name':u'the-child', 'title':u'The Child'},
                                 ])
        theparent = model.Package.by_name(u'the-parent')
        thechild = model.Package.by_name(u'the-child')
        rev = model.repo.new_revision()
        thechild.add_relationship(u'child_of', theparent, u'Some comment')
        model.repo.commit_and_remove()

        theparent = model.Package.by_name(u'the-parent')
        thechild = model.Package.by_name(u'the-child')
        assert len(thechild.get_relationships()) == 1, thechild.get_relationships()
        pr = thechild.get_relationships()[0]
        assert theparent.get_relationships() == [pr], theparent.relationships
        assert thechild.relationships_as_subject == [pr], thechild.relationships_as_subject
        assert thechild.get_relationships(direction='forward') == [pr], thechild.get_relationships(direction='forward')
        assert not thechild.relationships_as_object, thechild.relationships_as_object
        assert not thechild.get_relationships(direction='reverse'), thechild.get_relationships(direction='reverse')
        assert not theparent.relationships_as_subject, theparent.relationships_as_subject
        assert theparent.relationships_as_object == [pr], theparent.relationships_as_object
        assert pr.type == u'child_of', pr.type
        assert pr.comment == u'Some comment', pr.comment
        assert pr.subject == thechild
        assert pr.object == theparent

    def test_reverse_creation(self):
        create = CreateTestData
        create.create_arbitrary([{'name':u'the-parent', 'title':u'The Parent'},
                                 {'name':u'the-child', 'title':u'The Child'},
                                 ])
        theparent = model.Package.by_name(u'the-parent')
        thechild = model.Package.by_name(u'the-child')
        rev = model.repo.new_revision()
        theparent.add_relationship(u'parent_of', thechild, u'Some comment')
        model.repo.commit_and_remove()

        theparent = model.Package.by_name(u'the-parent')
        thechild = model.Package.by_name(u'the-child')
        assert len(thechild.get_relationships()) == 1, thechild.get_relationships()
        pr = thechild.get_relationships()[0]
        assert pr.type == u'child_of', pr.type
        assert pr.comment == u'Some comment', pr.comment
        assert pr.subject == thechild
        assert pr.object == theparent

    def test_types(self):
        create = CreateTestData
        create.create_arbitrary([{'name':u'pkga', 'title':u'The Parent'},
                                 {'name':u'pkgb', 'title':u'The Child'},
                                 ])
        pkga = model.Package.by_name(u'pkga')
        pkgb = model.Package.by_name(u'pkgb')
        rev = model.repo.new_revision()
        pkgb.add_relationship(u'parent_of', pkga)
        pkgb.add_relationship(u'has_derivation', pkga)
        pkgb.add_relationship(u'child_of', pkga)
        pkgb.add_relationship(u'depends_on', pkga)
        model.repo.commit_and_remove()
        # i.e.  pkga child_of pkgb
        #       pkga derives_from pkgb
        #       pkgb child_of pkga
        #       pkgb depends_on pkga

        pkga = model.Package.by_name(u'pkga')
        pkgb = model.Package.by_name(u'pkgb')
        assert len(pkga.relationships_as_subject) == 2, pkga.relationships_as_subject
        assert len(pkgb.relationships_as_subject) == 2, pkga.relationships_as_subject
        assert len(pkga.relationships_as_object) == 2, pkga.relationships_as_object
        assert len(pkgb.relationships_as_object) == 2, pkga.relationships_as_object
        assert len(pkga.get_relationships()) == 4, pkga.get_relationships()
        assert len(pkgb.get_relationships()) == 4, pkgb.get_relationships()
        rel1, rel2 = pkga.relationships_as_subject if pkga.relationships_as_subject[0].type == u'child_of' else pkga.relationships_as_subject[::-1]
        assert rel1.type == u'child_of', rel1.type
        assert rel1.subject == pkga, rel1.subject
        assert rel1.object == pkgb, rel1.type
        assert rel2.type == u'derives_from', rel2.type
        assert rel2.subject == pkga, rel2.subject
        assert rel2.object == pkgb, rel2.type
        rel3, rel4 = pkga.relationships_as_object if pkga.relationships_as_object[0].type == u'child_of' else pkga.relationships_as_object[::-1]
        assert rel3.type == u'child_of', rel3.type
        assert rel3.subject == pkgb, rel3.subject
        assert rel3.object == pkga, rel3.type
        assert rel4.type == u'depends_on', rel4.type
        assert rel4.subject == pkgb, rel4.subject
        assert rel4.object == pkga, rel4.type

class TestSimple:
    @classmethod
    def setup_class(self):
        create = CreateTestData
        create.create_arbitrary([
            {'name':u'pkga', 'title':u'The Parent'},
            {'name':u'pkgb', 'title':u'The Child'},
            {'name':u'pkgc', 'title':u'The Child\s Child'},
            ])
        pkga = model.Package.by_name(u'pkga')
        pkgb = model.Package.by_name(u'pkgb')
        pkgc = model.Package.by_name(u'pkgc')
        rev = model.repo.new_revision()
        pkgb.add_relationship(u'parent_of', pkga)
        pkgb.add_relationship(u'has_derivation', pkga)
        pkgb.add_relationship(u'child_of', pkga)
        pkgb.add_relationship(u'depends_on', pkga)
        pkgc.add_relationship(u'child_of', pkgb)
        model.repo.commit_and_remove()

        self.pkga = model.Package.by_name(u'pkga')
        self.pkgb = model.Package.by_name(u'pkgb')
        self.pkgc = model.Package.by_name(u'pkgc')

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()

    def test_usage(self):
        pkga_subject_query = model.PackageRelationship.by_subject(self.pkga)
        assert pkga_subject_query.count() == 2
        for rel in pkga_subject_query:
            assert rel.subject == self.pkga

        pkgb_object_query = model.PackageRelationship.by_object(self.pkgb)
        assert pkgb_object_query.count() == 3, pkgb_object_query.count()
        for rel in pkgb_object_query:
            assert rel.object == self.pkgb

class TestComplicated:
    @classmethod
    def setup_class(self):
        create = CreateTestData
        create.create_family_test_data()

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()

    def test_rels(self):
        rels = model.Package.by_name(u'homer').relationships
        assert len(rels) == 5, '%i: %s' % (len(rels), [rel for rel in rels])
        def check(rels, subject, type, object):
            for rel in rels:
                if rel.subject.name == subject and rel.type == type and rel.object.name == object:
                    return
            assert 0, 'Could not find relationship in: %r' % rels
        check(rels, 'homer', 'child_of', 'abraham')
        check(rels, 'bart', 'child_of', 'homer')
        check(rels, 'lisa', 'child_of', 'homer')
        check(rels, 'homer_derived', 'derives_from', 'homer')
        check(rels, 'homer', 'depends_on', 'beer')
        rels = model.Package.by_name(u'bart').relationships
        assert len(rels) == 1, len(rels)
        check(rels, 'bart', 'child_of', 'homer')

        pkgc_subject_query = model.PackageRelationship.by_subject(self.pkgc)
        assert pkgc_subject_query.count() == 1, pkgc_subject_query.count()
        for rel in pkgc_subject_query:
            assert rel.subject == self.pkgc

    def test_relationships_with(self):
        rels = self.pkgb.get_relationships_with(self.pkgc)
        assert len(rels) == 1, rels
        assert rels[0].type == 'child_of'

        rels = self.pkgb.get_relationships_with(self.pkga)
        assert len(rels) == 4, rels

        rels = self.pkgb.get_relationships_with(self.pkgc, type=u'parent_of')
        assert len(rels) == 1, rels

        rels = self.pkgb.get_relationships_with(self.pkgc, type=u'child_of')
        assert len(rels) == 0, rels

        rels = self.pkgc.get_relationships_with(self.pkgb, type=u'child_of')
        assert len(rels) == 1, rels

    def test_types(self):
        all_types = model.PackageRelationship.get_all_types()
        assert len(all_types) >= 6
        assert all_types[0] == u'depends_on', all_types

class TestComplicated:
    @classmethod
    def setup_class(self):
        create = CreateTestData
        create.create_family_test_data()

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()

    def _check(self, rels, subject, type, object):
        for rel in rels:
            if rel.subject.name == subject and rel.type == type and rel.object.name == object:
                return
        assert 0, 'Could not find relationship in: %r' % rels

    def test_01_rels(self):
        "audit the simpsons family relationships"
        rels = model.Package.by_name(u'homer').get_relationships()
        assert len(rels) == 5, '%i: %s' % (len(rels), [rel for rel in rels])

        self._check(rels, 'homer', 'child_of', 'abraham')
        self._check(rels, 'bart', 'child_of', 'homer')
        self._check(rels, 'lisa', 'child_of', 'homer')
        self._check(rels, 'homer_derived', 'derives_from', 'homer')
        self._check(rels, 'homer', 'depends_on', 'beer')
        rels = model.Package.by_name(u'bart').get_relationships()
        assert len(rels) == 2, len(rels)
        self._check(rels, 'bart', 'child_of', 'homer')
        self._check(rels, 'bart', 'child_of', 'marge')

    def test_02_deletion(self):
        "delete bart is child of homer"
        rels = model.Package.by_name(u'bart').get_relationships()
        assert len(rels) == 2
        assert rels[0].state == model.State.ACTIVE


        model.repo.new_revision()
        rels[0].delete()
        rels[1].delete()
        model.repo.commit_and_remove()

        rels = model.Package.by_name(u'bart').get_relationships()
        assert len(rels) == 0

        bart = model.Package.by_name(u'bart')
        q = model.Session.query(model.PackageRelationship).filter_by(subject=bart)
        assert q.count() == 2
        assert q.first().state == model.State.DELETED
        q = q.filter_by(state=model.State.ACTIVE)
        assert q.count() == 0

    def test_03_recreate(self):
        "recreate bart is child of homer"
        bart = model.Package.by_name(u"bart")
        homer = model.Package.by_name(u"homer")
        marge = model.Package.by_name(u"marge")

        rels = bart.get_relationships()
        assert len(rels) == 0, "expected bart to have no relations, found %s" % rels

        model.repo.new_revision()
        bart.add_relationship(u"child_of", homer)
        bart.add_relationship(u"child_of", marge)
        model.repo.commit_and_remove()

        rels = bart.get_relationships()
        assert len(rels) == 2, "expected bart to have one relation, found %s" % rels

        q = model.Session.query(model.PackageRelationship).filter_by(subject=bart)
        count = q.count()
        assert count == 2, "bart has %d relationships, expected 2" % count
        active = q.filter_by(state=model.State.ACTIVE).count()
        assert active == 2, "bart has %d active relationships, expected 2" % active
        deleted = q.filter_by(state=model.State.DELETED).count()
        assert deleted == 0, "bart has %d deleted relationships, expect 0" % deleted

    def test_04_relationship_display(self):

        bart = model.Package.by_name(u"bart")
        assert len(bart.get_relationships_printable()) == 3, len(bart.get_relationships_printable())

        model.repo.new_revision()
        lisa = model.Package.by_name(u"lisa")
        lisa.state = 'deleted'
        model.Session.commit()

        bart = model.Package.by_name(u"bart")
        assert len(bart.get_relationships_printable()) == 2, len(bart.get_relationships_printable())

    def test_05_revers_recreation(self):
        homer = model.Package.by_name(u"homer")
        homer_derived = model.Package.by_name(u"homer_derived")
        rels = homer.get_relationships(with_package=homer_derived)
        self._check(rels, 'homer_derived', 'derives_from', 'homer')

        model.repo.new_revision()
        rels[0].delete()
        model.repo.commit_and_remove()
        rels = homer.get_relationships(with_package=homer_derived)
        assert len(homer.get_relationships(with_package=homer_derived)) == 0, \
            'expectiong homer to have no relationships'

        model.repo.new_revision()
        homer.add_relationship(u"derives_from", homer_derived)
        model.repo.commit_and_remove()
        rels = homer.get_relationships(with_package=homer_derived)
        assert len(homer.get_relationships(with_package=homer_derived)) == 1, \
            'expectiong homer to have newly created relationship'
        self._check(rels, 'homer', 'derives_from', 'homer_derived')

        model.repo.new_revision()
        rels[0].delete()
        model.repo.commit_and_remove()
        model.repo.new_revision()
        homer.add_relationship(u"has_derivation", homer_derived)
        model.repo.commit_and_remove()
        rels = homer.get_relationships(with_package=homer_derived)
        assert len(homer.get_relationships(with_package=homer_derived)) == 1, \
            'expectiong homer to have recreated initial relationship'
        self._check(rels, 'homer_derived', 'derives_from', 'homer')
