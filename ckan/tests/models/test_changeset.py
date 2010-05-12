from ckan.tests import *
from ckan.model.changeset import ChangesetRegister, Changeset
from ckan.model.changeset import ChangeRegister, Change
from ckan.model.changeset import Range, Intersection, Heads, Sum, Merge
from ckan.model.changeset import AutoResolve, AutoResolvePreferClosing
from ckan.model.changeset import ConflictException
from ckan.model.changeset import UncommittedChangesException
from ckan.model.changeset import WorkingAtHeadException
from ckan.model.changeset import RevisionRegister, PackageRegister
import ckan.model as model
from ckan.model import setup_default_user_roles

class TestCase(object):

    def setup(self):
        model.repo.clean_db()
        model.repo.rebuild_db()
        model.Session.remove()

    def teardown(self):
        model.Session.remove()

    def assert_true(self, value):
        assert value, "Not true: '%s'" % value

    def assert_false(self, value):
        assert not value, "Not false: '%s'" % value

    def assert_equal(self, value1, value2):
        assert value1 == value2, "Not equal: %s" % ((value1, value2),)

    def assert_isinstance(self, value, check):
        assert isinstance(value, check), "Not an instance: %s" % ((value, check),)
    
    def assert_raises(self, exception_class, callable, *args, **kwds): 
        try:
            callable(*args, **kwds)
        except exception_class:
            pass
        else:
            assert False, "Didn't raise '%s' when calling: %s with %s" % (exception_class, callable, (args, kwds))


class TestChangesetRegister(TestCase):

    def setup(self):
        super(TestChangesetRegister, self).setup()
        self.changesets = ChangesetRegister()
        self.revisions = RevisionRegister()
        self.packages = PackageRegister()
        self.changes = ChangeRegister()

    def teardown(self):
        return
        self.changesets = None
        for name in [u'annie', u'annie1', u'annie2']:
            annie = self.packages.get(name, None, attr='name')
            if annie:
                annie.purge()
        model.Session.commit()
        model.Session.remove()
        super(TestChangesetRegister, self).teardown()
   
    def test_commit(self):
        revision_id = self.build_creating_revision()
        revision = self.revisions[revision_id]
        changeset_ids = self.changesets.commit()
        print changeset_ids
        working = self.changesets.get_working()
        self.assert_true(working)
        print working.id
        self.assert_equal(len(changeset_ids), 2)
        changeset0 = self.changesets.get(changeset_ids[0])
        self.assert_false(changeset0.is_working)
        changeset1 = self.changesets.get(changeset_ids[1])
        self.assert_true(changeset1.is_working)
        self.assert_equal(changeset0.id, changeset1.follows_id)
        
    def test_update(self):
        self.assert_false(self.changesets.get_working())
        changeset_id = self.build_creating_changeset()
        self.assert_raises(UncommittedChangesException, self.changesets.update)
        new_changeset_ids = self.changesets.commit()
        self.assert_equal(len(new_changeset_ids), 1)
        self.assert_raises(WorkingAtHeadException, self.changesets.update)
        self.assert_true(self.changesets.get_working())
        self.assert_equal(self.changesets.get_working().id, new_changeset_ids[0])
        changeset_id = self.build_creating_changeset('1', follows_id=self.changesets.get_working().id)
        self.assert_equal(len(self.packages), 0)
        report = {}
        self.changesets.update(report=report)
        # Check changesets have been applied.
        self.assert_equal(len(report['created']), 1)
        self.assert_equal(len(self.packages), 1)
        self.assert_equal(self.changesets.get_working().id, changeset_id)
        self.assert_raises(WorkingAtHeadException, self.changesets.update)

    def test_construct_from_revision(self):
        revision_id = self.build_creating_revision()
        revision = self.revisions[revision_id]
        changeset_id = self.changesets.construct_from_revision(revision)
        changeset = self.changesets.get(changeset_id)
        self.assert_isinstance(changeset, Changeset)
        self.assert_true(changeset.revision_id)
        self.assert_true(changeset.changes)
        
        revision_id = self.build_creating_revision('1')
        revision = self.revisions[revision_id]
        changeset_id = self.changesets.construct_from_revision(revision)
        changeset = self.changesets.get(changeset_id)
        self.assert_isinstance(changeset, Changeset)
        self.assert_true(changeset.revision_id)
        self.assert_true(changeset.changes)

        revision_id = self.build_updating_revision('', 'and also')
        revision = self.revisions[revision_id]
        changeset_id = self.changesets.construct_from_revision(revision)
        changeset = self.changesets.get(changeset_id)
        self.assert_isinstance(changeset, Changeset)
        self.assert_true(changeset.revision_id)
        self.assert_true(changeset.changes)

        revision_id = self.build_updating_revision('1', 'and now')
        revision = self.revisions[revision_id]
        changeset_id = self.changesets.construct_from_revision(revision)
        changeset = self.changesets.get(changeset_id)
        self.assert_isinstance(changeset, Changeset)
        self.assert_true(changeset.revision_id)
        self.assert_true(changeset.changes)

        data = changeset.as_dict()
        self.assert_true(data['id'])
        self.assert_true(data['meta'])
        self.assert_true(data['changes'])
        meta = data['meta']
        self.assert_true('log_message' in meta)
        self.assert_true('author' in meta)
        self.assert_true('timestamp' in meta)
        changes = data['changes']
        self.assert_true(changes[0]['ref'])
        self.assert_true(changes[0]['diff'])
        diff = changes[0]['diff']
        self.assert_true(diff['new'])
        self.assert_true(diff['old'])

    def test_conflict(self):
        self.assert_equal(len(self.packages), 0)
        changeset_id = self.build_creating_changeset()
        changeset = self.changesets[changeset_id]
        count_before = len(self.revisions)
        self.assert_false(changeset.revision_id)
        revision_id = changeset.apply()
        revision = self.revisions[revision_id]
        self.assert_true(changeset.revision_id)
        count_after = len(self.revisions)
        self.assert_isinstance(revision, model.Revision)
        self.assert_equal(count_after - count_before, 1)
        self.assert_true(revision.packages)
        package = revision.packages[0]
        self.assert_equal(package.id, "5872c628-435e-4896-ad04-514aab3d0d10")
        self.assert_equal(package.name, "annie")
        self.assert_equal(package.title, "Annie Get Your Coat (orig)")
        self.assert_equal(package.license_id, "open-orig")

        self.assert_equal(len(self.packages), 1)

        changeset_id = self.build_creating_changeset("1")
        changeset = self.changesets[changeset_id]
        count_before = len(self.revisions)
        self.assert_false(changeset.revision_id)
        revision_id = changeset.apply()
        revision = self.revisions[revision_id]
        self.assert_true(changeset.revision_id)
        count_after = len(self.revisions)
        self.assert_isinstance(revision, model.Revision)
        self.assert_equal(count_after - count_before, 1)
        self.assert_true(revision.packages)
        package = revision.packages[0]
        self.assert_equal(package.id, "5872c628-435e-4896-ad04-514aab3d0d11")
        self.assert_equal(package.name, "annie1")
        self.assert_equal(package.title, "Annie Get Your Coat (orig)")
        self.assert_equal(package.license_id, "open-orig")

        self.assert_equal(len(self.packages), 2)

        changeset_id = self.build_conflicting_changeset("", "orig", "corr")
        changeset = self.changesets[changeset_id]
        self.assert_true(changeset.is_conflicting())
        self.assert_false(changeset.revision_id)
        self.assert_raises(ConflictException, changeset.apply)
        self.assert_false(changeset.revision_id)
        revision_id = changeset.apply(is_forced=True)
        revision = self.revisions[revision_id]
        self.assert_true(changeset.revision_id)
        package = revision.packages[0]
        self.assert_equal(package.id, "5872c628-435e-4896-ad04-514aab3d0d10")
        self.assert_equal(package.name, "annie")
        self.assert_equal(package.title, "Annie Get Your Coat (corr)")
        self.assert_equal(package.license_id, "closed-corr")

        self.assert_equal(len(self.packages), 2)

        changeset_id = self.build_conflicting_changeset("1", "orig", "corr")
        changeset = self.changesets[changeset_id]
        self.assert_true(changeset.is_conflicting())
        self.assert_false(changeset.revision_id)
        self.assert_raises(ConflictException, changeset.apply)
        self.assert_false(changeset.revision_id)
        revision_id = changeset.apply(is_forced=True)
        revision = self.revisions[revision_id]
        self.assert_true(changeset.revision_id)
        package = revision.packages[0]
        self.assert_equal(package.id, "5872c628-435e-4896-ad04-514aab3d0d11")
        self.assert_equal(package.name, "annie1")
        self.assert_equal(package.title, "Annie Get Your Coat (corr)")
        self.assert_equal(package.license_id, "closed-corr")

    def test_apply(self):
        self.assert_equal(len(self.packages), 0)
        changeset_id = self.build_creating_changeset()
        changeset = self.changesets[changeset_id]
        count_before = len(self.revisions)
        self.assert_false(changeset.revision_id)
        revision_id = changeset.apply()
        revision = self.revisions[revision_id]
        self.assert_true(changeset.revision_id)
        count_after = len(self.revisions)
        self.assert_isinstance(revision, model.Revision)
        self.assert_equal(count_after - count_before, 1)
        self.assert_true(revision.packages)
        package = revision.packages[0]
        self.assert_equal(package.id, "5872c628-435e-4896-ad04-514aab3d0d10")
        self.assert_equal(package.name, "annie")
        self.assert_equal(package.title, "Annie Get Your Coat (orig)")
        self.assert_equal(package.license_id, "open-orig")

        self.assert_equal(len(self.packages), 1)

        changeset_id = self.build_creating_changeset("1")
        changeset = self.changesets[changeset_id]
        count_before = len(self.revisions)
        self.assert_false(changeset.revision_id)
        revision_id = changeset.apply()
        revision = self.revisions[revision_id]
        self.assert_true(changeset.revision_id)
        count_after = len(self.revisions)
        self.assert_isinstance(revision, model.Revision)
        self.assert_equal(count_after - count_before, 1)
        self.assert_true(revision.packages)
        package = revision.packages[0]
        self.assert_equal(package.id, "5872c628-435e-4896-ad04-514aab3d0d11")
        self.assert_equal(package.name, "annie1")
        self.assert_equal(package.title, "Annie Get Your Coat (orig)")
        self.assert_equal(package.license_id, "open-orig")

        self.assert_equal(len(self.packages), 2)
        
        changeset_id = self.build_updating_changeset("", "orig", "corr")
        changeset = self.changesets[changeset_id]
        count_before = len(self.revisions)
        self.assert_false(changeset.revision_id)
        revision_id = changeset.apply()
        revision = self.revisions[revision_id]
        self.assert_true(changeset.revision_id)
        count_after = len(self.revisions)
        self.assert_isinstance(revision, model.Revision)
        self.assert_equal(count_after - count_before, 1)
        self.assert_true(revision.packages)
        package = revision.packages[0]
        self.assert_equal(package.id, "5872c628-435e-4896-ad04-514aab3d0d10")
        self.assert_equal(package.name, "annie")
        self.assert_equal(package.title, "Annie Get Your Coat (corr)")
        self.assert_equal(package.license_id, "open-corr")

        self.assert_equal(len(self.packages), 2)

        changeset_id = self.build_updating_changeset("1", "orig", "corr")
        count_before = len(self.revisions)
        changeset = self.changesets[changeset_id]
        self.assert_false(changeset.revision_id)
        revision_id = changeset.apply()
        revision = self.revisions[revision_id]
        self.assert_true(changeset.revision_id)
        count_after = len(self.revisions)
        self.assert_isinstance(revision, model.Revision)
        self.assert_equal(count_after - count_before, 1)
        self.assert_true(revision.packages)
        package = revision.packages[0]
        self.assert_equal(package.id, "5872c628-435e-4896-ad04-514aab3d0d11")
        self.assert_equal(package.name, "annie1")
        self.assert_equal(package.title, "Annie Get Your Coat (corr)")
        self.assert_equal(package.license_id, "open-corr")

        self.assert_equal(len(self.packages), 2)

        changeset_id = self.build_updating_changeset("", "corr", "draft")
        changeset = self.changesets[changeset_id]
        count_before = len(self.revisions)
        self.assert_false(changeset.revision_id)
        revision_id = changeset.apply()
        revision = self.revisions[revision_id]
        self.assert_true(changeset.revision_id)
        count_after = len(self.revisions)
        self.assert_isinstance(revision, model.Revision)
        self.assert_equal(count_after - count_before, 1)
        self.assert_true(revision.packages)
        package = revision.packages[0]
        self.assert_equal(package.id, "5872c628-435e-4896-ad04-514aab3d0d10")
        self.assert_equal(package.name, "annie")
        self.assert_equal(package.title, "Annie Get Your Coat (draft)")
        self.assert_equal(package.license_id, "open-draft")

        self.assert_equal(len(self.packages), 2)

        changeset_id = self.build_updating_changeset("1", "corr", "draft")
        changeset = self.changesets[changeset_id]
        count_before = len(self.revisions)
        self.assert_false(changeset.revision_id)
        revision_id = changeset.apply()
        revision = self.revisions[revision_id]
        self.assert_true(changeset.revision_id)
        count_after = len(self.revisions)
        self.assert_isinstance(revision, model.Revision)
        self.assert_equal(count_after - count_before, 1)
        self.assert_true(revision.packages)
        package = revision.packages[0]
        self.assert_equal(package.id, "5872c628-435e-4896-ad04-514aab3d0d11")
        self.assert_equal(package.name, "annie1")
        self.assert_equal(package.title, "Annie Get Your Coat (draft)")
        self.assert_equal(package.license_id, "open-draft")

        self.assert_equal(len(self.packages), 2)

    def build_creating_revision(self, mark=''):
        revision = self.revisions.create_entity(author=u'test', log_message=u'test')
        package = self.packages.create_entity(name=u'annie%s'%mark, title=u'Annie Get Your Coat (%s)'%mark)
        model.Session.add(package)
        model.Session.commit()
        model.Session.remove()
        setup_default_user_roles(package, [])
        self.assert_true(revision.id)
        self.assert_true(package.id)
        self.assert_true(revision.packages)
        return revision.id

    def build_updating_revision(self, mark='', vary_new=''):
        revision = self.revisions.create_entity(author=u'test', log_message=u'test')
        package = self.packages.get(u'annie%s'%mark, attr="name")
        package.title = u'Annie Get Your Coat (%s)' % vary_new
        model.Session.commit()
        model.Session.remove()
        self.assert_true(revision.id)
        self.assert_true(package.id)
        self.assert_true(revision.packages)
        return revision.id

    def build_creating_changeset(self, mark='', follows_id=None):
        id = u"5872c628-435e-4896-ad04-514aab3d0d10"
        if mark:
            assert len(mark) == 1
            id = list(id)
            id[-1] = mark
            id = u"".join(id)
        vary = 'orig'
        diff = u"""{
            "old": null,
            "new": {
                "name": "annie%s",
                "title": "Annie Get Your Coat (%s)",
                "license_id": "open-%s"
            }
        }""" % (mark, vary, vary)
        ref = u"/package/%s" % id
        change = self.changes.create_entity(diff=diff, ref=ref)
        changeset = self.changesets.create_entity(
            follows_id=follows_id,
            changes=[change], 
        )
        model.Session.add(changeset)
        model.Session.commit()
        assert changeset.id
        return changeset.id

    def build_updating_changeset(self, mark='', vary_old='', vary_new='', follows_id=None):
        id = u"5872c628-435e-4896-ad04-514aab3d0d10"
        if mark:
            assert len(mark) == 1
            id = list(id)
            id[-1] = mark
            id = u"".join(id)
        diff = u"""{
            "old": {
                "title": "Annie Get Your Coat (%s)",
                "license_id": "open-%s"
            },
            "new": {
                "title": "Annie Get Your Coat (%s)",
                "license_id": "open-%s"
            }
        }""" % (vary_old, vary_old, vary_new, vary_new)
        ref = u"/package/%s" % id
        change = self.changes.create_entity(diff=diff, ref=ref)
        changeset = self.changesets.create_entity(
            follows_id=follows_id,
            changes=[change],
        )
        model.Session.add(changeset)
        model.Session.commit()
        return changeset.id

    def build_conflicting_changeset(self, mark='', vary_old='', vary_new='', follows_id=None):
        id = u"5872c628-435e-4896-ad04-514aab3d0d10"
        if mark:
            assert len(mark) == 1
            id = list(id)
            id[-1] = mark
            id = u"".join(id)
        diff = u"""{
            "old": {
                "title": "Annie Get Your Coat (%s)",
                "license_id": "closed-%s"
            },
            "new": {
                "title": "Annie Get Your Coat (%s)",
                "license_id": "closed-%s"
            }
        }""" % (vary_old, vary_old, vary_new, vary_new)
        ref = u"/package/%s" % id
        change = self.changes.create_entity(diff=diff, ref=ref)
        changeset = self.changesets.create_entity(
            follows_id=follows_id,
            changes=[change],
        )
        model.Session.add(changeset)
        model.Session.commit()
        return changeset.id

    def test_add_unseen(self):
        changeset_data = {
            "id": "8772c628-435e-4896-ad04-514aab3d0d10",
            "meta": {},
            "changes": [
                {
                    "ref": "/package/4662c628-435e-4896-ad04-514aab3d0e66",
                    "diff": {
                        "new": {
                            "name": "coat",
                            "title": "Annie Get Your Coat",
                            "license_id": "abcd3"
                        },
                        "old": {}
                    },

                }
            ]
        }
        changeset_id = self.changesets.add_unseen(changeset_data)
        changeset = ChangesetRegister()[changeset_id]


class TestChangeset(TestCase):

    def setup(self):
        self.changeset = Changeset()
        model.Session.add(self.changeset)
        model.Session.commit()

    def teardown(self):
        self.changeset.purge()
        model.Session.commit()
        model.Session.remove()
   

class TestChange(TestCase):

    def setup(self):
        diff = u"""{
            "new": {
                "id": "f711c90b-6406-498b-8ddc-2d9e33dc25b9",
                "name": "annie"
            },
            "old": null
        }"""
        self.change = Change(ref=u'/package/f711c90b-6406-498b-8ddc-2d9e33dc25b9', diff=diff)
        model.Session.add(self.change)
        model.Session.commit()

    def teardown(self):
        self.change.purge()
        model.Session.commit()
        model.Session.remove()
   

class TestArithmetic(TestCase):

    def setup(self):
        self.name0 = 'namezero'
        self.name1 = 'nameone'
        self.name2 = 'nametwo'
        self.name3 = 'namethree'
        self.name4 = 'namefour'
        self.title0 = 'Title Zero'
        self.title1 = 'Title One'
        self.title2 = 'Title Two'
        self.title3 = 'Title Three'
        self.title4 = 'Title Four'
        # 0. Create package 'z'.
        self.change0 = self.creating_package_change(id='z', name=self.name0, title=self.title0)
        self.cs0 = self.create_cs(changes=[self.change0])
        model.Session.commit()
        # 1. Create package 'a'.
        self.change1 = self.creating_package_change(id='a', name=self.name1, title=self.title1)
        self.cs1 = self.create_cs(follows_id=self.cs0.id, changes=[self.change1])
        model.Session.commit()
        # 2. Update package 'a' title.
        self.change2 = self.updating_title_change(id='a', old=self.title1, new=self.title2)
        self.cs2 = self.create_cs(follows_id=self.cs1.id, changes=[self.change2])
        model.Session.commit()
        # 3. Update package 'a' title again.
        self.change3 = self.updating_title_change(id='a', old=self.title2, new=self.title3)
        self.cs3 = self.create_cs(follows_id=self.cs2.id, changes=[self.change3])
        model.Session.commit()
        # 4. Update package 'a' name.
        self.change4 = self.updating_name_change(id='a', old=self.name1, new=self.name2)
        self.cs4 = self.create_cs(follows_id=self.cs1.id, changes=[self.change4])
        model.Session.commit()
        # 5. Update package 'a' name again.
        self.change5 = self.updating_name_change(id='a', old=self.name2, new=self.name3)
        self.cs5 = self.create_cs(follows_id=self.cs4.id, changes=[self.change5])
        model.Session.commit()
        # 6. Branch title changes from cs2.
        self.change6 = self.updating_title_change(id='a', old=self.title2, new=self.title4)
        self.cs6 = self.create_cs(follows_id=self.cs2.id, changes=[self.change6])
        model.Session.commit()
        # 7. Branch name changes from cs4.
        self.change7 = self.updating_name_change(id='a', old=self.name2, new=self.name4)
        self.cs7 = self.create_cs(follows_id=self.cs4.id, changes=[self.change7])
        model.Session.commit()
        print "Changeset0 : %s" % self.cs0.id
        print "Changeset1 : %s" % self.cs1.id
        print "Changeset2 : %s" % self.cs2.id
        print "Changeset3 : %s" % self.cs3.id
        print "Changeset4 : %s" % self.cs4.id
        print "Changeset5 : %s" % self.cs5.id
        print "Changeset6 : %s" % self.cs6.id
        print "Changeset7 : %s" % self.cs7.id

    def teardown(self):
        model.repo.clean_db()
        model.repo.rebuild_db()
        model.Session.remove()

    def test_range1_2(self):
        range = self.create_range(self.cs1, self.cs2)
        changes = range.calc_changes()
        self.assert_equal(len(changes), 1)
        change = changes[0]
        self.assert_false(change.old)
        self.assert_true(change.new)
        self.assert_equal(change.new['title'], self.title2)

    def test_range2_3(self):
        range = self.create_range(self.cs2, self.cs3)
        changes = range.calc_changes()
        self.assert_equal(len(changes), 1)
        change = changes[0]
        self.assert_true(change.old)
        self.assert_equal(change.old['title'], self.title1)
        self.assert_true(change.new)
        self.assert_equal(change.new['title'], self.title3)

    def test_range1_3(self):
        range = self.create_range(self.cs1, self.cs3)
        changes = range.calc_changes()
        self.assert_equal(len(changes), 1)
        change = changes[0]
        self.assert_false(change.old)
        self.assert_true(change.new)
        self.assert_equal(change.new['title'], self.title3)
        # Test the 'pop_first' method.
        range.pop_first()
        changes = range.calc_changes()
        self.assert_equal(len(changes), 1)
        change = changes[0]
        self.assert_true(change.old)
        self.assert_equal(change.old['title'], self.title1)
        self.assert_true(change.new)
        self.assert_equal(change.new['title'], self.title3)

    def test_intersection_1_1(self):
        intersection = self.create_intersection(self.cs1, self.cs1)
        changeset = intersection.find()
        self.assert_true(changeset)
        self.assert_equal(changeset.id, self.cs1.id)

    def test_intersection_1_2(self):
        intersection = self.create_intersection(self.cs1, self.cs2)
        changeset = intersection.find()
        self.assert_true(changeset)
        self.assert_equal(changeset.id, self.cs1.id)

    def test_intersection_2_1(self):
        intersection = self.create_intersection(self.cs2, self.cs1)
        changeset = intersection.find()
        self.assert_true(changeset)
        self.assert_equal(changeset.id, self.cs1.id)

    def test_intersection_2_3(self):
        intersection = self.create_intersection(self.cs2, self.cs3)
        changeset = intersection.find()
        self.assert_true(changeset)
        self.assert_equal(changeset.id, self.cs2.id)

    def test_intersection_3_2(self):
        intersection = self.create_intersection(self.cs3, self.cs2)
        changeset = intersection.find()
        self.assert_true(changeset)
        self.assert_equal(changeset.id, self.cs2.id)

    def test_intersection_4_2(self):
        intersection = self.create_intersection(self.cs4, self.cs2)
        changeset = intersection.find()
        self.assert_true(changeset)
        self.assert_equal(changeset.id, self.cs1.id)

    def test_intersection_2_4(self):
        intersection = self.create_intersection(self.cs2, self.cs4)
        changeset = intersection.find()
        self.assert_true(changeset)
        self.assert_equal(changeset.id, self.cs1.id)

    def test_intersection_3_5(self):
        intersection = self.create_intersection(self.cs3, self.cs5)
        changeset = intersection.find()
        self.assert_true(changeset)
        self.assert_equal(changeset.id, self.cs1.id)

    def test_intersection_5_3(self):
        intersection = self.create_intersection(self.cs5, self.cs3)
        changeset = intersection.find()
        self.assert_true(changeset)
        self.assert_equal(changeset.id, self.cs1.id)

    def test_heads(self):
        ids = Heads().ids()
        print "Heads: %s" % ids
        self.assert_equal(len(ids), 4)
        self.assert_true(self.cs3.id in ids)
        self.assert_true(self.cs5.id in ids)
        self.assert_true(self.cs6.id in ids)
        self.assert_true(self.cs7.id in ids)
        self.assert_false(self.cs0.id in ids)
        self.assert_false(self.cs1.id in ids)
        self.assert_false(self.cs2.id in ids)
        self.assert_false(self.cs4.id in ids)

    def test_sum1(self):
        range1 = self.create_range(self.cs1, self.cs1)
        range2 = self.create_range(self.cs1, self.cs1)
        sum = Sum(range1.calc_changes(), range2.calc_changes())
        self.assert_raises(ConflictException, sum.detect_conflict)
        self.assert_true(sum.is_conflicting())

    def test_sum1(self):
        range1 = self.create_range(self.cs0, self.cs1)
        range2 = self.create_range(self.cs1, self.cs1)
        sum = Sum(range1.calc_changes(), range2.calc_changes())
        self.assert_raises(ConflictException, sum.detect_conflict)
        self.assert_true(sum.is_conflicting())

    def test_sum2(self):
        range1 = self.create_range(self.cs2, self.cs3)
        range2 = self.create_range(self.cs4, self.cs5)
        sum = Sum(range1.calc_changes(), range2.calc_changes())
        sum.detect_conflict()
        self.assert_false(sum.is_conflicting())
        changes = sum.calc_changes()
        self.assert_equal(len(changes), 1)
        self.assert_equal(changes[0].new['name'], 'namethree')
        self.assert_equal(changes[0].new['title'], 'Title Three')
    
    def test_resolve(self):
        resolve = self.create_resolve(self.cs5, self.cs3)
        changes = resolve.calc_changes()
        self.assert_equal(len(changes), 0)

        resolve = self.create_resolve(self.cs6, self.cs3)
        changes = resolve.calc_changes()
        self.assert_equal(len(changes), 1)
        change = changes[0]
        self.assert_equal(change.old['title'], self.title4)
        self.assert_equal(change.new['title'], self.title3)

        resolve = self.create_resolve(self.cs5, self.cs7)
        changes = resolve.calc_changes()
        self.assert_equal(len(changes), 1)
        change = changes[0]
        self.assert_equal(change.old['name'], self.name3)
        self.assert_equal(change.new['name'], self.name4)

    def test_merge_non_conflicting(self):
        merge = Merge(closing=self.cs5, continuing=self.cs3)
        self.assert_false(merge.is_conflicting())
        mergeset = merge.create_mergeset()
        self.assert_true(mergeset.id)
        self.assert_equal(mergeset.follows_id, self.cs3.id)
        self.assert_equal(mergeset.closes_id, self.cs5.id)
        changes = mergeset.changes
        print changes
        self.assert_equal(len(changes), 1)
        self.assert_equal(changes[0].old['name'], 'nameone')
        self.assert_equal(changes[0].new['name'], 'namethree')
        self.assert_false('title' in changes[0].new)
        self.assert_true(mergeset.get_meta().get('log_message'))
        self.assert_true(mergeset.get_meta().get('author'))
        # More tests to calculate Range from cs0 to mergeset.
        model.Session.commit()
        range = Range(self.cs0, mergeset)
        changes = range.calc_changes()
        self.assert_equal(len(changes), 2)
        changes0 = changes[0]
        changes1 = changes[1]
        self.assert_false(changes0.old)
        self.assert_false(changes1.old)
        self.assert_true(changes0.new)
        self.assert_true(changes1.new)
        self.assert_true(changes0.new['name'] in [self.name0, self.name3])
        self.assert_true(changes1.new['name'] in [self.name0, self.name3])
        self.assert_true(changes0.new['name'] != changes1.new['name'])
        if changes0.new['name'] == self.name0:
            self.assert_equal(changes0.new['title'], self.title0)
        elif changes0.new['name'] == self.name3:
            self.assert_equal(changes0.new['title'], self.title3)
        if changes1.new['name'] == self.name0:
            self.assert_equal(changes1.new['title'], self.title0)
        elif changes1.new['name'] == self.name3:
            self.assert_equal(changes1.new['title'], self.title3)

    def test_merge_conflicting(self):
        merge = Merge(closing=self.cs6, continuing=self.cs3)
        self.assert_true(merge.is_conflicting())
        mergeset = merge.create_mergeset(resolve_class=AutoResolve)
        self.assert_true(mergeset.id)
        self.assert_equal(mergeset.follows_id, self.cs3.id)
        self.assert_equal(mergeset.closes_id, self.cs6.id)
        changes = mergeset.changes
        self.assert_equal(len(mergeset.changes), 0)
        self.assert_true(mergeset.get_meta().get('log_message'))
        self.assert_true(mergeset.get_meta().get('author'))

        merge = Merge(closing=self.cs6, continuing=self.cs3)
        self.assert_true(merge.is_conflicting())
        mergeset = merge.create_mergeset(resolve_class=AutoResolvePreferClosing)
        self.assert_true(mergeset.id)
        self.assert_equal(mergeset.follows_id, self.cs3.id)
        self.assert_equal(mergeset.closes_id, self.cs6.id)
        changes = mergeset.changes
        self.assert_equal(len(mergeset.changes), 1)
        self.assert_true(mergeset.get_meta().get('log_message'))
        self.assert_true(mergeset.get_meta().get('author'))


    def create_resolve(self, changeset1, changeset2):
        intersection = self.create_intersection(changeset1, changeset2)
        ancestor = intersection.find()
        range1 = self.create_range(ancestor, changeset1)
        range2 = self.create_range(ancestor, changeset2)
        range1.pop_first()
        range2.pop_first()
        changes1 = range1.calc_changes()
        changes2 = range2.calc_changes()
        return AutoResolve(changes1, changes2)

    def create_range(self, start, stop):
        return Range(start, stop)

    def create_intersection(self, child1, child2):
        return Intersection(child1, child2)

    def create_cs(self, **kwds):
        cs = ChangesetRegister().create_entity(**kwds)
        model.Session.commit()
        return cs

    def creating_package_change(self, id='a', name='annie', title='My Title'):
        diff = u"""{
            "old": null,
            "new": {
                "id": "%s711c90b-6406-498b-8ddc-2d9e33dc25b9",
                "name": "%s",
                "title": "%s"
            }
        }""" % (id, name, title)
        change = Change(ref=u'/package/%s711c90b-6406-498b-8ddc-2d9e33dc25b9' % id, diff=diff)
        model.Session.add(change)
        return change

    def updating_title_change(self, id='a', old='My Title', new='My New Title'):
        diff = u"""{
            "old": {
                "title": "%s"
            },
            "new": {
                "title": "%s"
            }
        }""" % (old, new)
        change = Change(ref=u'/package/%s711c90b-6406-498b-8ddc-2d9e33dc25b9' % id, diff=diff)
        model.Session.add(change)
        return change

    def updating_name_change(self, id='a', old='annie', new='any'):
        diff = u"""{
            "old": {
                "name": "%s"
            },
            "new": {
                "name": "%s"
            }
        }""" % (old, new)
        change = Change(ref=u'/package/%s711c90b-6406-498b-8ddc-2d9e33dc25b9' % id, diff=diff)
        model.Session.add(change)
        return change

