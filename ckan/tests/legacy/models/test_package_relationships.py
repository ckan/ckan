# encoding: utf-8

import pytest
import ckan.model as model
from ckan.lib.create_test_data import CreateTestData


@pytest.mark.usefixtures("clean_db")
class TestCreation(object):
    def test_normal_creation(self):
        create = CreateTestData
        create.create_arbitrary(
            [
                {"name": "the-parent", "title": "The Parent"},
                {"name": "the-child", "title": "The Child"},
            ]
        )
        theparent = model.Package.by_name("the-parent")
        thechild = model.Package.by_name("the-child")
        thechild.add_relationship("child_of", theparent, "Some comment")
        model.repo.commit_and_remove()

        theparent = model.Package.by_name("the-parent")
        thechild = model.Package.by_name("the-child")
        assert (
            len(thechild.get_relationships()) == 1
        ), thechild.get_relationships()
        pr = thechild.get_relationships()[0]
        assert theparent.get_relationships() == [pr], theparent.relationships
        assert thechild.relationships_as_subject == [
            pr
        ], thechild.relationships_as_subject
        assert thechild.get_relationships(direction="forward") == [
            pr
        ], thechild.get_relationships(direction="forward")
        assert (
            not thechild.relationships_as_object
        ), thechild.relationships_as_object
        assert not thechild.get_relationships(
            direction="reverse"
        ), thechild.get_relationships(direction="reverse")
        assert (
            not theparent.relationships_as_subject
        ), theparent.relationships_as_subject
        assert theparent.relationships_as_object == [
            pr
        ], theparent.relationships_as_object
        assert pr.type == "child_of", pr.type
        assert pr.comment == "Some comment", pr.comment
        assert pr.subject == thechild
        assert pr.object == theparent

    def test_reverse_creation(self):
        create = CreateTestData
        create.create_arbitrary(
            [
                {"name": "the-parent", "title": "The Parent"},
                {"name": "the-child", "title": "The Child"},
            ]
        )
        theparent = model.Package.by_name("the-parent")
        thechild = model.Package.by_name("the-child")
        theparent.add_relationship("parent_of", thechild, "Some comment")
        model.repo.commit_and_remove()

        theparent = model.Package.by_name("the-parent")
        thechild = model.Package.by_name("the-child")
        assert (
            len(thechild.get_relationships()) == 1
        ), thechild.get_relationships()
        pr = thechild.get_relationships()[0]
        assert pr.type == "child_of", pr.type
        assert pr.comment == "Some comment", pr.comment
        assert pr.subject == thechild
        assert pr.object == theparent

    def test_types(self):
        create = CreateTestData
        create.create_arbitrary(
            [
                {"name": "pkga", "title": "The Parent"},
                {"name": "pkgb", "title": "The Child"},
            ]
        )
        pkga = model.Package.by_name("pkga")
        pkgb = model.Package.by_name("pkgb")
        pkgb.add_relationship("parent_of", pkga)
        pkgb.add_relationship("has_derivation", pkga)
        pkgb.add_relationship("child_of", pkga)
        pkgb.add_relationship("depends_on", pkga)
        model.repo.commit_and_remove()
        # i.e.  pkga child_of pkgb
        #       pkga derives_from pkgb
        #       pkgb child_of pkga
        #       pkgb depends_on pkga

        pkga = model.Package.by_name("pkga")
        pkgb = model.Package.by_name("pkgb")
        assert (
            len(pkga.relationships_as_subject) == 2
        ), pkga.relationships_as_subject
        assert (
            len(pkgb.relationships_as_subject) == 2
        ), pkga.relationships_as_subject
        assert (
            len(pkga.relationships_as_object) == 2
        ), pkga.relationships_as_object
        assert (
            len(pkgb.relationships_as_object) == 2
        ), pkga.relationships_as_object
        assert len(pkga.get_relationships()) == 4, pkga.get_relationships()
        assert len(pkgb.get_relationships()) == 4, pkgb.get_relationships()
        rel1, rel2 = (
            pkga.relationships_as_subject
            if pkga.relationships_as_subject[0].type == "child_of"
            else pkga.relationships_as_subject[::-1]
        )
        assert rel1.type == "child_of", rel1.type
        assert rel1.subject == pkga, rel1.subject
        assert rel1.object == pkgb, rel1.type
        assert rel2.type == "derives_from", rel2.type
        assert rel2.subject == pkga, rel2.subject
        assert rel2.object == pkgb, rel2.type
        rel3, rel4 = (
            pkga.relationships_as_object
            if pkga.relationships_as_object[0].type == "child_of"
            else pkga.relationships_as_object[::-1]
        )
        assert rel3.type == "child_of", rel3.type
        assert rel3.subject == pkgb, rel3.subject
        assert rel3.object == pkga, rel3.type
        assert rel4.type == "depends_on", rel4.type
        assert rel4.subject == pkgb, rel4.subject
        assert rel4.object == pkga, rel4.type


@pytest.mark.usefixtures("clean_db")
class TestSimple(object):
    def test_usage(self):
        create = CreateTestData
        create.create_arbitrary(
            [
                {"name": "pkga", "title": "The Parent"},
                {"name": "pkgb", "title": "The Child"},
                {"name": "pkgc", "title": "The Child\s Child"},
            ]
        )
        pkga = model.Package.by_name("pkga")
        pkgb = model.Package.by_name("pkgb")
        pkgc = model.Package.by_name("pkgc")
        pkgb.add_relationship("parent_of", pkga)
        pkgb.add_relationship("has_derivation", pkga)
        pkgb.add_relationship("child_of", pkga)
        pkgb.add_relationship("depends_on", pkga)
        pkgc.add_relationship("child_of", pkgb)
        model.repo.commit_and_remove()

        pkga = model.Package.by_name("pkga")
        pkgb = model.Package.by_name("pkgb")
        pkgc = model.Package.by_name("pkgc")

        pkga_subject_query = model.PackageRelationship.by_subject(pkga)
        assert pkga_subject_query.count() == 2
        for rel in pkga_subject_query:
            assert rel.subject == pkga

        pkgb_object_query = model.PackageRelationship.by_object(pkgb)
        assert pkgb_object_query.count() == 3, pkgb_object_query.count()
        for rel in pkgb_object_query:
            assert rel.object == pkgb


@pytest.mark.usefixtures("clean_db")
class TestComplicated(object):
    def _check(self, rels, subject, type, object):
        for rel in rels:
            if (
                rel.subject.name == subject
                and rel.type == type
                and rel.object.name == object
            ):
                return
        assert 0, "Could not find relationship in: %r" % rels

    def test_01_rels(self):
        create = CreateTestData
        create.create_family_test_data()

        "audit the simpsons family relationships"
        rels = model.Package.by_name("homer").get_relationships()
        assert len(rels) == 5, "%i: %s" % (len(rels), [rel for rel in rels])

        self._check(rels, "homer", "child_of", "abraham")
        self._check(rels, "bart", "child_of", "homer")
        self._check(rels, "lisa", "child_of", "homer")
        self._check(rels, "homer_derived", "derives_from", "homer")
        self._check(rels, "homer", "depends_on", "beer")
        rels = model.Package.by_name("bart").get_relationships()
        assert len(rels) == 2, len(rels)
        self._check(rels, "bart", "child_of", "homer")
        self._check(rels, "bart", "child_of", "marge")

        # def test_02_deletion(self):
        "delete bart is child of homer"
        rels = model.Package.by_name("bart").get_relationships()
        assert len(rels) == 2
        assert rels[0].state == model.State.ACTIVE

        rels[0].delete()
        rels[1].delete()
        model.repo.commit_and_remove()

        rels = model.Package.by_name("bart").get_relationships()
        assert len(rels) == 0

        bart = model.Package.by_name("bart")
        q = model.Session.query(model.PackageRelationship).filter_by(
            subject=bart
        )
        assert q.count() == 2
        assert q.first().state == model.State.DELETED
        q = q.filter_by(state=model.State.ACTIVE)
        assert q.count() == 0

        # def test_03_recreate(self):
        "recreate bart is child of homer"
        bart = model.Package.by_name("bart")
        homer = model.Package.by_name("homer")
        marge = model.Package.by_name("marge")

        rels = bart.get_relationships()
        assert len(rels) == 0, (
            "expected bart to have no relations, found %s" % rels
        )

        bart.add_relationship("child_of", homer)
        bart.add_relationship("child_of", marge)
        model.repo.commit_and_remove()

        rels = bart.get_relationships()
        assert len(rels) == 2, (
            "expected bart to have one relation, found %s" % rels
        )

        q = model.Session.query(model.PackageRelationship).filter_by(
            subject=bart
        )
        count = q.count()
        assert count == 2, "bart has %d relationships, expected 2" % count
        active = q.filter_by(state=model.State.ACTIVE).count()
        assert active == 2, (
            "bart has %d active relationships, expected 2" % active
        )
        deleted = q.filter_by(state=model.State.DELETED).count()
        assert deleted == 0, (
            "bart has %d deleted relationships, expect 0" % deleted
        )

        # def test_04_relationship_display(self):

        bart = model.Package.by_name("bart")
        assert len(bart.get_relationships_printable()) == 3, len(
            bart.get_relationships_printable()
        )

        lisa = model.Package.by_name("lisa")
        lisa.state = "deleted"
        model.Session.commit()

        bart = model.Package.by_name("bart")
        assert len(bart.get_relationships_printable()) == 2, len(
            bart.get_relationships_printable()
        )

        # def test_05_revers_recreation(self):
        homer = model.Package.by_name("homer")
        homer_derived = model.Package.by_name("homer_derived")
        rels = homer.get_relationships(with_package=homer_derived)
        self._check(rels, "homer_derived", "derives_from", "homer")

        rels[0].delete()
        model.repo.commit_and_remove()
        rels = homer.get_relationships(with_package=homer_derived)
        assert (
            len(homer.get_relationships(with_package=homer_derived)) == 0
        ), "expectiong homer to have no relationships"

        homer.add_relationship("derives_from", homer_derived)
        model.repo.commit_and_remove()
        rels = homer.get_relationships(with_package=homer_derived)
        assert (
            len(homer.get_relationships(with_package=homer_derived)) == 1
        ), "expectiong homer to have newly created relationship"
        self._check(rels, "homer", "derives_from", "homer_derived")

        rels[0].delete()
        model.repo.commit_and_remove()
        homer.add_relationship("has_derivation", homer_derived)
        model.repo.commit_and_remove()
        rels = homer.get_relationships(with_package=homer_derived)
        assert (
            len(homer.get_relationships(with_package=homer_derived)) == 1
        ), "expectiong homer to have recreated initial relationship"
        self._check(rels, "homer_derived", "derives_from", "homer")
