from ckan.tests import *
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
        assert len(thechild.relationships) == 1, thechild.relationships
        pr = thechild.relationships[0]
        assert theparent.relationships == [pr], theparent.relationships
        assert thechild.relationships_as_subject == [pr], thechild.relationships_as_subject
        assert not thechild.relationships_as_object, thechild.relationships_as_object
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
        assert len(thechild.relationships) == 1, thechild.relationships
        pr = thechild.relationships[0]
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
        assert len(pkga.relationships) == 4, pkga.relationships
        assert len(pkgb.relationships) == 4, pkgb.relationships
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

        self.pkga = model.Package.by_name(u'pkga')
        self.pkgb = model.Package.by_name(u'pkgb')

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()

    def test_usage(self):
        pkga_subject_query = model.PackageRelationship.by_subject(self.pkga)
        assert pkga_subject_query.count() == 2
        for rel in pkga_subject_query:
            assert rel.subject == self.pkga
            
        pkgb_object_query = model.PackageRelationship.by_object(self.pkgb)
        assert pkgb_object_query.count() == 2
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
        assert len(rels) == 5, '%i: %s' % (len(rels), [str(rel) for rel in rels])
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
        
