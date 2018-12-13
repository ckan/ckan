import logging
# logging.basicConfig(level=logging.DEBUG)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('vdm')

from sqlalchemy.orm import object_session, class_mapper

import vdm.sqlalchemy
from demo import *

from sqlalchemy import __version__ as sqav
if sqav.startswith("0.4"):
    _clear = Session.clear
else:
    _clear = Session.expunge_all
    
class Test_01_SQLAlchemySession:
    @classmethod
    def setup_class(self):
        repo.rebuild_db()
    @classmethod
    def teardown_class(self):
        Session.remove()

    def test_1(self):
        assert not hasattr(Session, 'revision')
        assert vdm.sqlalchemy.SQLAlchemySession.at_HEAD(Session)
        rev = Revision()
        vdm.sqlalchemy.SQLAlchemySession.set_revision(Session, rev)
        assert vdm.sqlalchemy.SQLAlchemySession.at_HEAD(Session)
        assert Session.revision is not None
        out = vdm.sqlalchemy.SQLAlchemySession.get_revision(Session)
        assert out == rev
        out = vdm.sqlalchemy.SQLAlchemySession.get_revision(Session())
        assert out == rev
        assert vdm.sqlalchemy.SQLAlchemySession.at_HEAD(Session)
        assert vdm.sqlalchemy.SQLAlchemySession.at_HEAD(Session())
        Session.remove()


class Test_02_Versioning:
    @classmethod
    def setup_class(self):
        repo.rebuild_db()

        logger.debug('===== STARTING REV 1')
        session = Session()
        rev1 = Revision()
        session.add(rev1)
        vdm.sqlalchemy.SQLAlchemySession.set_revision(session, rev1)

        self.name1 = 'anna'
        self.name2 = 'warandpeace'
        self.title1 = 'XYZ'
        self.title2 = 'ABC'
        self.notes1 = u'Here\nare some\nnotes'
        self.notes2 = u'Here\nare no\nnotes'
        lic1 = License(name='blah', open=True)
        lic1.revision = rev1
        lic2 = License(name='foo', open=True)
        p1 = Package(name=self.name1, title=self.title1, license=lic1, notes=self.notes1)
        p2 = Package(name=self.name2, title=self.title1, license=lic1)
        session.add_all([lic1,lic2,p1,p2])

        logger.debug('***** Committing/Flushing Rev 1')
        session.commit()
        # can only get it after the flush
        self.rev1_id = rev1.id
        _clear()
        Session.remove()

        logger.debug('===== STARTING REV 2')
        session = Session()
        rev2 = Revision()
        session.add(rev2)
        vdm.sqlalchemy.SQLAlchemySession.set_revision(session, rev2)
        outlic1 = Session.query(License).filter_by(name='blah').first()
        outlic2 = Session.query(License).filter_by(name='foo').first()
        outlic2.open = False
        outp1 = Session.query(Package).filter_by(name=self.name1).one()
        outp2 = Session.query(Package).filter_by(name=self.name2).one()
        outp1.title = self.title2
        outp1.notes = self.notes2
        outp1.license = outlic2
        t1 = Tag(name='geo')
        session.add_all([outp1,outp2,t1])
        outp1.tags = [t1]
        outp2.delete()
        # session.flush()
        session.commit()
        # must do this after flush as timestamp not set until then
        self.ts2 = rev2.timestamp
        self.rev2_id = rev2.id
        Session.remove()

    @classmethod
    def teardown_class(self):
        Session.remove()

    def test_revisions_exist(self):
        revs = Session.query(Revision).all()
        assert len(revs) == 2
        # also check order (youngest first)
        assert revs[0].timestamp > revs[1].timestamp

    def test_revision_youngest(self):
        rev = Revision.youngest(Session)
        assert rev.timestamp == self.ts2

    def test_basic(self):
        assert Session.query(License).count() == 2, Session.query(License).count()
        assert Session.query(Package).count() == 2, Session.query(Package).count()
        assert hasattr(LicenseRevision, 'revision_id')
        assert Session.query(LicenseRevision).count() == 3, Session.query(LicenseRevision).count()
        assert Session.query(PackageRevision).count() == 4, Session.query(PackageRevision).count()

    def test_all_revisions(self):
        p1 = Session.query(Package).filter_by(name=self.name1).one()
        assert len(p1.all_revisions) == 2
        # problem here is that it might pass even if broken because ordering of
        # uuid ids is 'right' 
        revs = [ pr.revision for pr in p1.all_revisions ]
        assert revs[0].timestamp > revs[1].timestamp, revs

    def test_basic_2(self):
        # should be at HEAD (i.e. rev2) by default 
        p1 = Session.query(Package).filter_by(name=self.name1).one()
        assert p1.license.open == False
        assert p1.revision.timestamp == self.ts2
        # assert p1.tags == []
        assert len(p1.tags) == 1

    def test_basic_continuity(self):
        p1 = Session.query(Package).filter_by(name=self.name1).one()
        pr1 = Session.query(PackageRevision).filter_by(name=self.name1).first()
        table = class_mapper(PackageRevision).mapped_table
        print table.c.keys()
        print pr1.continuity_id
        assert pr1.continuity == p1

    def test_basic_state(self):
        p1 = Session.query(Package).filter_by(name=self.name1).one()
        p2 = Session.query(Package).filter_by(name=self.name2).one()
        assert p1.state
        assert p1.state == State.ACTIVE
        assert p2.state == State.DELETED

    def test_versioning_0(self):
        p1 = Session.query(Package).filter_by(name=self.name1).one()
        rev1 = Session.query(Revision).get(self.rev1_id)
        p1r1 = p1.get_as_of(rev1)
        assert p1r1.continuity == p1

    def test_versioning_1(self):
        p1 = Session.query(Package).filter_by(name=self.name1).one()
        rev1 = Session.query(Revision).get(self.rev1_id)
        p1r1 = p1.get_as_of(rev1)
        assert p1r1.name == self.name1
        assert p1r1.title == self.title1

    def test_traversal_normal_fks_and_state_at_same_time(self):
        p2 = Session.query(Package).filter_by(name=self.name2).one()
        rev1 = Session.query(Revision).get(self.rev1_id)
        p2r1 = p2.get_as_of(rev1)
        assert p2r1.state == State.ACTIVE

    def test_versioning_traversal_fks(self):
        p1 = Session.query(Package).filter_by(name=self.name1).one()
        rev1 = Session.query(Revision).get(self.rev1_id)
        p1r1 = p1.get_as_of(rev1)
        assert p1r1.license.open == True

    def test_versioning_m2m_1(self):
        p1 = Session.query(Package).filter_by(name=self.name1).one()
        rev1 = Session.query(Revision).get(self.rev1_id)
        ptag = p1.package_tags[0]
        # does not exist
        assert ptag.get_as_of(rev1) == None

    def test_versioning_m2m(self):
        p1 = Session.query(Package).filter_by(name=self.name1).one()
        rev1 = Session.query(Revision).get(self.rev1_id)
        p1r1 = p1.get_as_of(rev1)
        assert len(p1.tags_active) == 0
        # NB: deleted includes tags that were non-existent
        assert len(p1.tags_deleted) == 1
        assert len(p1.tags) == 0
        assert len(p1r1.tags) == 0
    
    def test_revision_has_state(self):
        rev1 = Session.query(Revision).get(self.rev1_id)
        assert rev1.state == State.ACTIVE

    def test_diff(self):
        p1 = Session.query(Package).filter_by(name=self.name1).one()
        pr2, pr1 = p1.all_revisions
        # pr1, pr2 = prs[::-1]
        
        diff = p1.diff_revisioned_fields(pr2, pr1, Package)
        assert diff['title'] == '- XYZ\n+ ABC', diff['title']
        assert diff['notes'] == '  Here\n- are some\n+ are no\n  notes', diff['notes']
        assert diff['license_id'] == '- 1\n+ 2', diff['license_id']

        diff1 = p1.diff(pr2.revision, pr1.revision)
        assert diff1 == diff, (diff1, diff)

        diff2 = p1.diff()
        assert diff2 == diff, (diff2, diff)

    def test_diff_2(self):
        '''Test diffing at a revision where just created.'''
        p1 = Session.query(Package).filter_by(name=self.name1).one()
        pr2, pr1 = p1.all_revisions

        diff1 = p1.diff(to_revision=pr1.revision)
        assert diff1['title'] == u'- None\n+ XYZ', diff1


class Test_03_StatefulVersioned:
    @classmethod
    def setup_class(self):
        repo.rebuild_db()
        logger.info('====== TestVersioning2: start')

        # create a package with some tags
        rev1 = repo.new_revision()
        self.name1 = 'anna'
        p1 = Package(name=self.name1)
        t1 = Tag(name='geo')
        t2 = Tag(name='geo2')
        p1.tags.append(t1)
        p1.tags.append(t2)
        Session.add_all([p1,t1,t2])
        Session.commit()
        self.rev1_id = rev1.id
        Session.remove()
        
        # now remove those tags
        logger.debug('====== start Revision 2')
        rev2 = repo.new_revision()
        newp1 = Session.query(Package).filter_by(name=self.name1).one()
        # either one works
        newp1.tags = []
        # newp1.tags_active.clear()
        assert len(newp1.tags_active) == 0
        Session.commit()
        self.rev2_id = rev2.id
        Session.remove()

        # now add one of them back
        logger.debug('====== start Revision 3')
        rev3 = repo.new_revision()
        newp1 = Session.query(Package).filter_by(name=self.name1).one()
        self.tagname1 = 'geo'
        t1 = Session.query(Tag).filter_by(name=self.tagname1).one()
        assert t1
        newp1.tags.append(t1)
        repo.commit_and_remove()

    @classmethod
    def teardown_class(self):
        Session.remove()

    def test_0_remove_and_readd_m2m(self):
        p1 = Session.query(Package).filter_by(name=self.name1).one()
        assert len(p1.package_tags) == 2, p1.package_tags
        assert len(p1.tags_active) == 1, p1.tags_active
        assert len(p1.tags) == 1
        Session.remove()

    def test_1_underlying_is_right(self):
        rev1 = Session.query(Revision).get(self.rev1_id)
        ptrevs = Session.query(PackageTagRevision).filter_by(revision_id=rev1.id).all()
        assert len(ptrevs) == 2
        for pt in ptrevs:
            assert pt.state == State.ACTIVE

        rev2 = Session.query(Revision).get(self.rev2_id)
        ptrevs = Session.query(PackageTagRevision).filter_by(revision_id=rev2.id).all()
        assert len(ptrevs) == 2
        for pt in ptrevs:
            assert pt.state == State.DELETED
    
    # test should be higher up but need at least 3 revisions for problem to
    # show up
    def test_2_get_as_of(self):
        p1 = Session.query(Package).filter_by(name=self.name1).one()
        rev2 = Session.query(Revision).get(self.rev2_id)
        # should be 2 deleted and 1 as None
        ptrevs = [ pt.get_as_of(rev2) for pt in p1.package_tags ]
        print ptrevs
        print Session.query(PackageTagRevision).all()
        assert ptrevs[0].revision_id == rev2.id

    def test_3_remove_and_readd_m2m_2(self):
        num_package_tags = 2
        rev1 = Session.query(Revision).get(self.rev1_id)
        p1 = Session.query(Package).filter_by(name=self.name1).one()
        p1rev = p1.get_as_of(rev1)
        # NB: relations on revision object proxy to continuity
        # (though with get_as_of revision set)
        assert len(p1rev.package_tags) == num_package_tags
        assert len(p1rev.tags) == 2
        Session.remove()

        rev2 = Session.query(Revision).get(self.rev2_id)
        p1 = Session.query(Package).filter_by(name=self.name1).one()
        p2rev = p1.get_as_of(rev2)
        assert p2rev.__class__ == PackageRevision
        assert len(p2rev.package_tags) == num_package_tags
        print rev2.id
        print p2rev.tags_active
        assert len(p2rev.tags) == 0


class Test_04_StatefulVersioned2:
    '''Similar to previous but setting m2m list using existing objects'''

    def setup(self):
        Session.remove()
        repo.rebuild_db()
        logger.info('====== TestStatefulVersioned2: start')

        # create a package with some tags
        rev1 = repo.new_revision()
        self.name1 = 'anna'
        p1 = Package(name=self.name1)
        t1 = Tag(name='geo')
        p1.tags.append(t1)
        Session.add_all([p1,t1])
        Session.commit()
        self.rev1_id = rev1.id
        Session.remove()

    def setup_method(self, name=''):
        self.setup()
        
    @classmethod
    def teardown_class(self):
        Session.remove()

    def _test_package_tags(self, check_all_pkg_tags=True):
        p1 = Session.query(Package).filter_by(name=self.name1).one()
        assert len(p1.package_tags) == 2, p1.package_tags
        all_pkg_tags = Session.query(PackageTag).all()
        if check_all_pkg_tags:
            assert len(all_pkg_tags) == 2

    def _test_tags(self):
        p1 = Session.query(Package).filter_by(name=self.name1).one()
        assert len(p1.tags) == 2, p1.tags

    def test_1(self):
        rev2 = repo.new_revision()
        newp1 = Session.query(Package).filter_by(name=self.name1).one()
        t1 = Session.query(Tag).filter_by(name='geo').one()
        t2 = Tag(name='geo2')
        newp1.tags = [ t1, t2 ]
        repo.commit_and_remove()

        self._test_package_tags()
        self._test_tags()
    
    def test_2(self):
        rev2 = repo.new_revision()
        newp1 = Session.query(Package).filter_by(name=self.name1).one()
        t1 = Session.query(Tag).filter_by(name='geo').one()
        t2 = Tag(name='geo2')
        print '**** setting tags'
        newp1.tags[:] = [ t1, t2 ]
        repo.commit_and_remove()

        # TODO: (?) check on No of PackageTags fails
        # the story is that an extra PackageTag for first tag gets constructed
        # even though existing in deleted state (as expected)
        # HOWEVER (unlike in 3 other cases in this class) this PackageTag is
        # *already committed* when it arrives at _check_for_existing_on_add and
        # therefore expunge has no effect on it (we'd need to delete and that
        # may start getting 'hairy' ...)
        self._test_package_tags(check_all_pkg_tags=False)
        self._test_tags()

    def test_3(self):
        rev2 = repo.new_revision()
        newp1 = Session.query(Package).filter_by(name=self.name1).one()
        t1 = Session.query(Tag).filter_by(name='geo').one()
        t2 = Tag(name='geo2')
        newp1.tags[0] = t1
        newp1.tags.append(t2)
        repo.commit_and_remove()

        self._test_package_tags()
        self._test_tags()

    def test_4(self):
        rev2 = repo.new_revision()
        newp1 = Session.query(Package).filter_by(name=self.name1).one()
        t1 = Session.query(Tag).filter_by(name='geo').one()
        t2 = Tag(name='geo2')
        newp1.tags = [ t1, t2 ]
        newp1.tags[0] = t1
        del newp1.tags[1]
        newp1.tags.append(t2)
        # NB: doing this the other way round will result in 3 PackageTags
        # newp1.tags.append(t2)
        # del newp1.tags[1]
        # this is because our system can't work out that we've just added and
        # deleted the same tag
        repo.commit_and_remove()

        self._test_package_tags()
        self._test_tags()


class Test_05_RevertAndPurge:

    @classmethod
    def setup_class(self):
        Session.remove()
        repo.rebuild_db()

        rev1 = Revision()
        Session.add(rev1)
        vdm.sqlalchemy.SQLAlchemySession.set_revision(Session, rev1)
        
        self.name1 = 'anna'
        p1 = Package(name=self.name1)
        p2 = Package(name='blahblah')
        Session.add_all([p1,p2])
        repo.commit_and_remove()

        self.name2 = 'warandpeace'
        self.lname = 'testlicense'
        rev2 = repo.new_revision()
        p1 = Session.query(Package).filter_by(name=self.name1).one()
        p1.name = self.name2
        l1 = License(name=self.lname)
        Session.add_all([p1,l1])
        repo.commit()
        self.rev2id = rev2.id
        Session.remove()

    @classmethod
    def teardown_class(self):
        Session.remove()
        repo.rebuild_db()

    def test_basics(self):
        revs = Session.query(Revision).all()
        assert len(revs) == 2
        p1 = Session.query(Package).filter_by(name=self.name2).one()
        assert p1.name == self.name2
        assert len(Session.query(Package).all()) == 2

    def test_list_changes(self):
        rev2 = Session.query(Revision).get(self.rev2id)
        out = repo.list_changes(rev2)
        assert len(out) == 3
        assert len(out[Package]) == 1, out
        assert len(out[License]) == 1, out

    def test_purge_revision(self):
        logger.debug('BEGINNING PURGE REVISION')
        Session.remove()
        rev2 = Session.query(Revision).get(self.rev2id)
        repo.purge_revision(rev2)
        revs = Session.query(Revision).all()
        assert len(revs) == 1
        p1 = Session.query(Package).filter_by(name=self.name1).first()
        assert p1 is not None
        assert len(Session.query(License).all()) == 0
        pkgs = Session.query(Package).all()
        assert len(pkgs) == 2, pkgrevs
        pkgrevs = Session.query(PackageRevision).all()
        assert len(pkgrevs) == 2, pkgrevs

