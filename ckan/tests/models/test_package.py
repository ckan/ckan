from nose.tools import assert_equal

from ckan.tests import *
import ckan.model as model

# Todo: More domain logic tests e.g. for isopen() and other domain logic.

class TestPackage:
    @classmethod
    def setup_class(self):
        CreateTestData.create()
        self.name = u'geodata'
        self.notes = 'A <b>great</b> package <script href="dodgy.js"/> like package:pollution_stats'
        pkgs = model.Session.query(model.Package).filter_by(name=self.name).all()
        for p in pkgs:
            p.purge()
        model.Session.commit()
        rev = model.repo.new_revision()
        self.pkg1 = model.Package(name=self.name)
        model.Session.add(self.pkg1)
        self.pkg1.notes = self.notes
        self.pkg1.license_id = u'odc-by'
        model.Session.commit()
        model.Session.remove()

    @classmethod
    def teardown_class(self):
        pkg1 = model.Session.query(model.Package).filter_by(name=self.name).one()
        
        pkg1.purge()
        model.Session.commit()
        model.repo.rebuild_db()
        model.Session.remove()

    def test_basic_revisioning(self):
        # create a package with package_fixture_data
        name = "frob"
        rev = model.repo.new_revision()
        package = model.Package(name=name)
        model.Session.add(package)
        model.Session.flush()
        revision_id = model.Session().revision.id
        timestamp = model.Session().revision.timestamp
        model.repo.commit_and_remove()

        package = model.Package.by_name(name)
        assert len(package.all_revisions) == 1
        assert package.all_revisions[0].revision_id == revision_id
        assert package.all_revisions[0].revision_timestamp == timestamp
        assert package.all_revisions[0].expired_id is None

        # change it
        rev = model.repo.new_revision()
        package = model.Package.by_name(name)
        package.title = "wobsnasm"
        revision_id2 = model.Session().revision.id
        timestamp2 = model.Session().revision.timestamp
        model.repo.commit_and_remove()

        package = model.Package.by_name(name)
        assert len(package.all_revisions) == 2
        assert package.all_revisions[0].revision_id == revision_id2
        assert package.all_revisions[0].revision_timestamp == timestamp2
        assert package.all_revisions[0].expired_id is None

        assert package.all_revisions[1].revision_id == revision_id
        assert package.all_revisions[1].revision_timestamp == timestamp
        assert package.all_revisions[1].expired_id == revision_id2

    def test_create_package(self):
        package = model.Package.by_name(self.name)
        assert package.name == self.name
        assert package.notes == self.notes
        assert package.license.id == u'odc-by'
        assert package.license.title == u'Open Data Commons Attribution License', package.license.title

    def test_update_package(self):
        newnotes = u'Written by Beethoven'
        author = u'jones'

        rev2 = model.repo.new_revision()
        pkg = model.Package.by_name(self.name)
        pkg.notes = newnotes
        rev2.author = u'jones'
        model.Session.commit()
        try:
            model.Session.expunge_all()
        except AttributeError: # sqlalchemy 0.4
            model.Session.clear()
        outpkg = model.Package.by_name(self.name)
        assert outpkg.notes == newnotes
        assert len(outpkg.all_revisions) > 0
        assert outpkg.all_revisions[0].revision.author == author

    def test_package_license(self):
        # Check unregistered license_id causes license to be 'None'.
        package = model.Package.by_name(self.name)
        package.license_id = u'zzzzzzz'
        assert package.license == None
        model.Session.remove() # forget change

    def test_as_dict(self):
        pkg = model.Package.by_name(self.name)
        out = pkg.as_dict()
        assert out['name'] == pkg.name
        assert out['license'] == pkg.license.title
        assert out['license_id'] == pkg.license.id
        assert out['tags'] == [tag.name for tag in pkg.get_tags()]
        assert out['metadata_modified'] == pkg.metadata_modified.isoformat()
        assert out['metadata_created'] == pkg.metadata_created.isoformat()
        assert_equal(out['notes'], pkg.notes)
        assert_equal(out['notes_rendered'], '<p>A great package  like <a href="/dataset/pollution_stats">package:pollution_stats</a>\n</p>')


class TestPackageWithTags:
    """
    WARNING: with sqlite these tests may fail (depending on the order they are
    run in) as sqlite does not support ForeignKeys properly.
    """
    # Todo: Remove comment, since it pertains to sqlite, which CKAN doesn't support?

    @classmethod
    def setup_class(self):
        model.repo.init_db()
        rev1 = model.repo.new_revision()
        self.tagname = u'test tag m2m!'
        self.tagname2 = u'testtagm2m2'
        self.tagname3 = u'test tag3!'
        self.pkgname = u'testpkgm2m'
        pkg = model.Package(name=self.pkgname)
        self.tag = model.Tag(name=self.tagname)
        self.tag2 = model.Tag(name=self.tagname2)
        pkg2tag = model.PackageTag(package=pkg, tag=self.tag)
        pkg.add_tag(self.tag2)
        model.Session.add_all([pkg,self.tag,self.tag2,pkg2tag])
        model.Session.commit()
        self.pkg2tag_id = pkg2tag.id
        self.rev = rev1

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()

    def test_1(self):
        pkg = model.Package.by_name(self.pkgname)
        assert len(pkg.get_tags()) == 2
        # pkg2tag = model.Session.query(model.PackageTag).get(self.pkg2tag_id)
        # assert pkg2tag.package.name == self.pkgname

    def test_tags(self):
        pkg = model.Package.by_name(self.pkgname)
        # TODO: go back to this
        # 2 default packages each with 2 tags so we have 2 + 4
        all = model.Session.query(model.Tag).all() 
        assert len(all) == 3, all

    def test_add_tag_by_name(self):
        rev = model.repo.new_revision()
        pkg = model.Package.by_name(self.pkgname)
        pkg.add_tag_by_name(self.tagname3)
        model.Session.commit()
        try:
            model.Session.expunge_all()
        except AttributeError: # sqlalchemy 0.4
            model.Session.clear()
        outpkg = model.Package.by_name(self.pkgname)
        assert len(outpkg.get_tags()) == 3
        t1 = model.Tag.by_name(self.tagname)
        assert len(t1.package_tags) == 1

    def test_add_tag_by_name_existing(self):
        try:
            model.Session.expunge_all()
        except AttributeError: # sqlalchemy 0.4
            model.Session.clear()
        pkg = model.Package.by_name(self.pkgname)
        assert len(pkg.get_tags()) == 3, len(pkg.get_tags())
        pkg.add_tag_by_name(self.tagname)
        assert len(pkg.get_tags()) == 3


class TestPackageTagSearch:
    @classmethod 
    def setup_class(self):
        CreateTestData.create()

        model.repo.new_revision()
        self.orderedfirst = u'000-zzz'
        # tag whose association will get deleted
        self.tagname = u'russian-tag-we-will-delete'
        tag3 = model.Tag(name=self.tagname)
        pkg = model.Package.by_name(u'annakarenina')
        pkg.add_tag(tag3)
        model.repo.commit_and_remove()

        model.repo.new_revision()
        pkg = model.Package.by_name(u'annakarenina')
        pkg.remove_tag(tag3)
        # now do a tag for ordering
        tagordered = model.Tag(name=self.orderedfirst)
        wap = model.Package.by_name(u'warandpeace')
        # do them the wrong way round
        wap.add_tag(tagordered)
        pkg.add_tag(tagordered)
        model.repo.commit_and_remove()

    @classmethod 
    def teardown_class(self):
        model.Session.remove()
        model.repo.rebuild_db()

    def test_0_deleted_package_tags(self):
        pkg = model.Package.by_name(u'annakarenina')
        tag = model.Tag.by_name(self.tagname)
        assert len(pkg.get_tags()) == 4, len(pkg.get_tags())
        assert len(tag.packages) == 0

    def test_1_tag_search_1(self):
        out = list(model.Tag.search_by_name(u'russian'))
        assert len(out) == 2
        assert out[0].name == 'russian'

    def test_1_tag_search_2(self):
        out = list(model.Tag.search_by_name(u'us'))
        assert len(out) == 2

    def test_1_tag_search_3(self):
        out = list(model.Tag.search_by_name(u's'))
        assert len(out) == 3
    
    def test_alphabetical_ordering(self):
        pkg = model.Package.by_name(u'annakarenina')
        tag = pkg.get_tags()[0]
        assert tag.name == self.orderedfirst
        assert tag.packages[0].name == 'annakarenina', tag.packages


class TestPackageRevisions:
    @classmethod
    def setup_class(self):
        model.Session.remove()
        model.repo.init_db()
        self.name = u'revisiontest'

        # create pkg
        self.notes = [u'Written by Puccini', u'Written by Rossini', u'Not written at all', u'Written again', u'Written off']
        rev = model.repo.new_revision()
        self.pkg1 = model.Package(name=self.name)
        model.Session.add(self.pkg1)
        self.pkg1.notes = self.notes[0]
        self.pkg1.extras['mykey'] = self.notes[0]
        model.repo.commit_and_remove()

        # edit pkg
        for i in range(5)[1:]:
            rev = model.repo.new_revision()
            pkg1 = model.Package.by_name(self.name)
            pkg1.notes = self.notes[i]
            pkg1.extras['mykey'] = self.notes[i]
            model.repo.commit_and_remove()

        self.pkg1 = model.Package.by_name(self.name)        

    @classmethod
    def teardown_class(self):
        rev = model.repo.new_revision()
        pkg1 = model.Package.by_name(self.name)
        pkg1.purge()
        model.repo.commit_and_remove()
        model.repo.rebuild_db()

    def test_1_all_revisions(self):
        all_rev = self.pkg1.all_revisions
        num_notes = len(self.notes)
        assert len(all_rev) == num_notes, len(all_rev)
        for i, rev in enumerate(all_rev):
            assert rev.notes == self.notes[num_notes - i - 1], '%s != %s' % (rev.notes, self.notes[i])
            #assert rev.extras['mykey'] == self.notes[num_notes - i - 1], '%s != %s' % (rev.extras['mykey'], self.notes[i])


class TestRelatedRevisions:
    @classmethod
    def setup_class(self):
        CreateTestData.create()
        model.Session.remove()
        self.name = u'difftest'

        # create pkg - PackageRevision
        rev = model.repo.new_revision()
        self.pkg1 = model.Package(name=self.name)
        model.Session.add(self.pkg1)
        self.pkg1.version = u'First version'
        model.repo.commit_and_remove()

        # edit pkg - PackageRevision
        rev = model.repo.new_revision()
        pkg1 = model.Package.by_name(self.name)
        pkg1.notes = u'New notes'
        rev.message = u'Added notes'
        model.repo.commit_and_remove()

        # edit pkg - PackageExtraRevision
        rev = model.repo.new_revision()
        pkg1 = model.Package.by_name(self.name)
        pkg1.extras = {u'a':u'b', u'c':u'd'}
        rev.message = u'Added extras'
        model.repo.commit_and_remove()

        # edit pkg - PackageTagRevision
        rev = model.repo.new_revision()
        pkg1 = model.Package.by_name(self.name)
        pkg1.add_tag_by_name(u'geo')
        pkg1.add_tag_by_name(u'scientific')
        rev.message = u'Added tags'
        model.repo.commit_and_remove()

        # edit pkg - ResourceRevision
        rev = model.repo.new_revision()
        pkg1 = model.Package.by_name(self.name)
        pkg1.resource_groups_all[0].resources_all.append(model.Resource(url=u'http://url1.com',
                                                    format=u'xls',
                                                    description=u'It is.',
                                                    hash=u'abc123'))
        rev.message = u'Added resource'
        model.repo.commit_and_remove()

        # edit pkg - ResourceRevision
        rev = model.repo.new_revision()
        pkg1 = model.Package.by_name(self.name)
        pkg1.resource_groups_all[0].resources_all[0].url = u'http://url1.com/edited'
        pkg1.resource_groups_all[0].resources_all.append(model.Resource(url=u'http://url2.com'))
        rev.message = u'Added resource'
        model.repo.commit_and_remove()

        # edit pkg - PackageRevision
        rev = model.repo.new_revision()
        pkg1 = model.Package.by_name(self.name)
        pkg1.notes = u'Changed notes'
        rev.message = u'Changed notes'
        model.repo.commit_and_remove()

        self.pkg1 = model.Package.by_name(self.name)
        self.res1 = model.Session.query(model.Resource).filter_by(url=u'http://url1.com/edited').one()
        self.res2 = model.Session.query(model.Resource).filter_by(url=u'http://url2.com').one()
        assert self.pkg1

    @classmethod
    def teardown_class(self):
        rev = model.repo.new_revision()
        pkg1 = model.Package.by_name(self.name)
        pkg1.purge()
        model.repo.commit_and_remove()
        model.repo.rebuild_db()

    def test_1_all_revisions(self):
        assert len(self.pkg1.all_revisions) == 3, self.pkg1.all_revisions
        assert len(self.pkg1.all_related_revisions) == 7, self.pkg1.all_related_revisions        

    def test_2_diff(self):
        rev_q = model.repo.history()
        rev_q = rev_q.order_by(model.Revision.timestamp.desc())
        last_rev = rev_q.first()
        first_rev = rev_q.all()[-1]
        second_rev = rev_q.all()[-2]
        diff = self.pkg1.diff(last_rev, second_rev)
        assert diff['notes'] == '- None\n+ Changed notes', diff['notes']
        assert diff.get('PackageTag-geo-state') == u'- \n+ active', diff
        assert diff.get('PackageTag-scientific-state') == u'- \n+ active', diff
        assert diff.get('PackageExtra-a-value') == u'- \n+ b', diff
        assert diff.get('PackageExtra-a-state') == u'- \n+ active', diff
        assert diff.get('PackageExtra-c-value') == u'- \n+ d', diff
        assert diff.get('PackageExtra-c-state') == u'- \n+ active', diff
        def test_res(diff, res, field, expected_value):
            key = 'Resource-%s-%s' % (res.id[:4], field)
            got_value = diff.get(key)
            expected_value = u'- \n+ %s' % expected_value
            assert got_value == expected_value, 'Key: %s Got: %r Expected: %r' % (key, got_value, expected_value)
        test_res(diff, self.res1, 'url', 'http://url1.com/edited')
        test_res(diff, self.res1, 'position', '0')
        test_res(diff, self.res1, 'format', 'xls')
        test_res(diff, self.res1, 'description', 'It is.')
        test_res(diff, self.res1, 'hash', 'abc123')
        test_res(diff, self.res1, 'state', 'active')
        test_res(diff, self.res2, 'url', 'http://url2.com')

class TestPackagePurge:
    @classmethod
    def setup_class(self):
        CreateTestData.create()
    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()
    def test_purge(self):
        pkgs = model.Session.query(model.Package).all()
        for p in pkgs:
           p.purge()
        model.Session.commit()
        pkgs = model.Session.query(model.Package).all()
        assert len(pkgs) == 0


