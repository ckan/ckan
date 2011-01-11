from ckan.tests.functional.api.base import *
from ckan.lib.create_test_data import CreateTestData
from ckan.tests import is_search_supported

class ModelApiTestCase(BaseModelApiTestCase):

    def setup(self):
        self.create_common_fixtures()
        self.init_extra_environ()
        self.source = None
        self.source1 = None
        self.source2 = None
        self.source3 = None
        self.source4 = None
        self.source5 = None
        self.job = None
        self.job1 = None
        self.job2 = None
        self.job3 = None

    def teardown(self):
        #self.rebuild()
        model.repo.clean_db()
        return
#        if self.job:
#            self.delete_commit(self.job)
#        if self.job1:
#            self.delete_commit(self.job1)
#        if self.job2:
#            self.delete_commit(self.job2)
#        if self.job3:
#            self.delete_commit(self.job3)
#        if self.source:
#            self.delete_commit(self.source)
#        if self.source1:
#            self.delete_commit(self.source1)
#        if self.source2:
#            self.delete_commit(self.source2)
#        if self.source3:
#            self.delete_commit(self.source3)
#        if self.source4:
#            self.delete_commit(self.source4)
#        if self.source5:
#            self.delete_commit(self.source5)
#        self.delete_common_fixtures()

    def test_02_get_tag_register_ok(self):
        # Test Packages Register Get 200.
        offset = self.offset('/rest/tag')
        res = self.app.get(offset, status=[200])
        assert 'russian' in res, res
        assert 'tolstoy' in res, res

    def test_02_get_group_register_ok(self):
        offset = self.offset('/rest/group')
        res = self.app.get(offset, status=[200])
        assert self.group_ref_from_name('david') in res, res
        assert self.group_ref_from_name('roger') in res, res

    def test_04_get_tag(self):
        offset = self.offset('/rest/tag/tolstoy')
        res = self.app.get(offset, status=[200])
        assert 'annakarenina' in res, res
        assert not 'warandpeace' in res, res

    def test_04_get_group(self):
        offset = self.offset('/rest/group/roger')
        res = self.app.get(offset, status=[200])
        assert self.package_ref_from_name('annakarenina') in res, res
        assert self.group_ref_from_name('roger') in res, res
        assert not self.package_ref_from_name('warandpeace') in res, res
        
    def test_05_get_group_entity_not_found(self):
        offset = self.offset('/rest/group/22222')
        res = self.app.get(offset, status=404)
        model.Session.remove()

    def test_05_get_tag_entity_not_found(self):
        offset = self.offset('/rest/tag/doesntexist')
        res = self.app.get(offset, status=404)
        model.Session.remove()

    def test_06_create_group_entity_ok(self):
        offset = self.offset('/rest/group')
        postparams = '%s=1' % self.dumps(self.testgroupvalues)
        res = self.app.post(offset, params=postparams, status=200,
                extra_environ=self.extra_environ)
        model.Session.remove()
        rev = model.repo.new_revision()
        group = model.Group.by_name(self.testgroupvalues['name'])
        assert group
        model.setup_default_user_roles(group, [self.user])
        model.repo.commit_and_remove()
        group = model.Group.by_name(self.testgroupvalues['name'])
        assert group
        assert group.title == self.testgroupvalues['title'], group
        assert group.description == self.testgroupvalues['description'], group
        assert len(group.packages) == 2, len(group.packages)
        anna = self.anna
        warandpeace = self.war
        assert anna in group.packages
        assert warandpeace in group.packages

        # Check group packages.
        offset = self.offset('/rest/group/%s' % self.testgroupvalues['name'])
        res = self.app.get(offset, status=[200])
        assert self.testgroupvalues['name'] in res, res
        assert self.package_ref_from_name(self.testgroupvalues['packages'][0]) in res, res
        ref = self.package_ref_from_name(self.testgroupvalues['packages'][0])
        assert ref in res, res
        ref = self.package_ref_from_name(self.testgroupvalues['packages'][1])
        assert ref in res, res
        model.Session.remove()
        
        # Check create group entity conflict.
        offset = self.offset('/rest/group')
        postparams = '%s=1' % self.dumps(self.testgroupvalues)
        res = self.app.post(offset, params=postparams, status=[409],
                extra_environ=self.extra_environ)
        model.Session.remove()

    def test_06_rate_package(self):
        # Test Rating Register Post 200.
        self.clear_all_tst_ratings()
        offset = self.offset('/rest/rating')
        rating_opts = {'package':u'warandpeace',
                       'rating':5}
        postparams = '%s=1' % self.dumps(rating_opts)
        res = self.app.post(offset, params=postparams, status=[200],
                extra_environ=self.extra_environ)
        model.Session.remove()
        pkg = self.get_package_by_name(rating_opts['package'])
        assert pkg
        assert len(pkg.ratings) == 1
        assert pkg.ratings[0].rating == rating_opts['rating'], pkg.ratings

        # Get package to see rating
        offset = self.offset('/rest/package/%s' % rating_opts['package'])
        res = self.app.get(offset, status=[200])
        assert rating_opts['package'] in res, res
        assert '"ratings_average": %s.0' % rating_opts['rating'] in res, res
        assert '"ratings_count": 1' in res, res
        
        model.Session.remove()
        
        # Rerate package
        offset = self.offset('/rest/rating')
        postparams = '%s=1' % self.dumps(rating_opts)
        res = self.app.post(offset, params=postparams, status=[200],
                extra_environ=self.extra_environ)
        model.Session.remove()
        pkg = self.get_package_by_name(rating_opts['package'])
        assert pkg
        assert len(pkg.ratings) == 1
        assert pkg.ratings[0].rating == rating_opts['rating'], pkg.ratings

    def test_06_rate_package_out_of_range(self):
        self.clear_all_tst_ratings()
        offset = self.offset('/rest/rating')
        rating_opts = {'package':u'warandpeace',
                       'rating':0}
        postparams = '%s=1' % self.dumps(rating_opts)
        res = self.app.post(offset, params=postparams, status=[400],
                extra_environ=self.extra_environ)
        model.Session.remove()
        pkg = self.get_package_by_name(rating_opts['package'])
        assert pkg
        assert len(pkg.ratings) == 0

    def test_10_edit_group(self):
        # create a group with testgroupvalues
        group = model.Group.by_name(self.testgroupvalues['name'])
        if not group:
            offset = self.offset('/rest/group')
            postparams = '%s=1' % self.dumps(self.testgroupvalues)
            res = self.app.post(offset, params=postparams, status=[200],
                    extra_environ=self.extra_environ)
            model.Session.remove()
            group = model.Group.by_name(self.testgroupvalues['name'])
        assert group
        assert len(group.packages) == 2, group.packages
        user = model.User.by_name(self.user_name)
        model.setup_default_user_roles(group, [user])

        # edit it
        group_vals = {'name':u'somethingnew', 'title':u'newtesttitle',
                      'packages':[u'annakarenina']}
        offset = self.offset('/rest/group/%s' % self.testgroupvalues['name'])
        postparams = '%s=1' % self.dumps(group_vals)
        res = self.app.post(offset, params=postparams, status=[200],
                            extra_environ=self.extra_environ)
        model.Session.remove()
        group = model.Session.query(model.Group).filter_by(name=group_vals['name']).one()
        assert group.name == group_vals['name']
        assert group.title == group_vals['title']
        assert len(group.packages) == 1, group.packages
        assert group.packages[0].name == group_vals['packages'][0]

    def test_10_edit_group_name_duplicate(self):
        # create a group with testgroupvalues
        if not model.Group.by_name(self.testgroupvalues['name']):
            rev = model.repo.new_revision()
            group = model.Group()
            model.Session.add(group)
            group.name = self.testgroupvalues['name']
            model.Session.commit()

            group = model.Group.by_name(self.testgroupvalues['name'])
            model.setup_default_user_roles(group, [self.user])
            rev = model.repo.new_revision()
            model.repo.commit_and_remove()
        assert model.Group.by_name(self.testgroupvalues['name'])
        
        # create a group with name 'dupname'
        dupname = u'dupname'
        if not model.Group.by_name(dupname):
            rev = model.repo.new_revision()
            group = model.Group()
            model.Session.add(group)
            group.name = dupname
            model.Session.commit()
        assert model.Group.by_name(dupname)

        # edit first group to have dupname
        group_vals = {'name':dupname}
        offset = self.offset('/rest/group/%s' % self.testgroupvalues['name'])
        postparams = '%s=1' % self.dumps(group_vals)
        res = self.app.post(offset, params=postparams, status=[409],
                            extra_environ=self.extra_environ)
        model.Session.remove()
        
    def test_11_delete_group(self):
        # Test Groups Entity Delete 200.

        # create a group with testgroupvalues
        group = model.Group.by_name(self.testgroupvalues['name'])
        if not group:
            rev = model.repo.new_revision()
            group = model.Group()
            model.Session.add(group)
            group.name = self.testgroupvalues['name']
            model.repo.commit_and_remove()

            rev = model.repo.new_revision()
            group = model.Group.by_name(self.testgroupvalues['name'])
            model.setup_default_user_roles(group, [self.user])
            model.repo.commit_and_remove()
        assert group
        user = model.User.by_name(self.user_name)
        model.setup_default_user_roles(group, [user])

        # delete it
        offset = self.offset('/rest/group/%s' % self.testgroupvalues['name'])
        res = self.app.delete(offset, status=[200],
                extra_environ=self.extra_environ)
        assert not model.Group.by_name(self.testgroupvalues['name'])
        model.Session.remove()

    def test_12_get_group_404(self):
        # Test Package Entity Get 404.
        assert not model.Session.query(model.Group).filter_by(name=self.testgroupvalues['name']).count()
        offset = self.offset('/rest/group/%s' % self.testgroupvalues['name'])
        res = self.app.get(offset, status=404)
        model.Session.remove()

    def test_13_delete_group_404(self):
        # Test Packages Entity Delete 404.
        assert not model.Session.query(model.Group).filter_by(name=self.testgroupvalues['name']).count()
        offset = self.offset('/rest/group/%s' % self.testgroupvalues['name'])
        res = self.app.delete(offset, status=[404],
                              extra_environ=self.extra_environ)

    def test_14_list_revisions(self):
        # Check mock register behaviour.
        offset = self.offset('/rest/revision')
        res = self.app.get(offset, status=200)
        revs = model.Session.query(model.Revision).all()
        assert revs, "There are no revisions in the model."
        res_dict = self.data_from_res(res)
        for rev in revs:
            assert rev.id in res_dict, (rev.id, res_dict)

    def test_14_get_revision(self):
        rev = model.repo.history().all()[-2] # 2nd revision is the creation of pkgs
        assert rev.id
        assert rev.timestamp.isoformat()
        offset = self.offset('/rest/revision/%s' % rev.id)
        response = self.app.get(offset, status=[200])
        response_data = self.data_from_res(response)
        assert rev.id == response_data['id']
        assert rev.timestamp.isoformat() == response_data['timestamp'], (rev.timestamp.isoformat(), response_data['timestamp'])
        assert 'packages' in response_data
        packages = response_data['packages']
        assert isinstance(packages, list)
        #assert len(packages) != 0, "Revision packages is empty: %s" % packages
        assert self.ref_package(self.anna) in packages, packages
        assert self.ref_package(self.war) in packages, packages

    def test_14_get_revision_404(self):
        revision_id = "xxxxxxxxxxxxxxxxxxxxxxxxxx"
        offset = self.offset('/rest/revision/%s' % revision_id)
        res = self.app.get(offset, status=404)
        model.Session.remove()

    def test_15_list_changesets(self):
        offset = self.offset('/rest/changeset')
        res = self.app.get(offset, status=[200])
        from ckan.model.changeset import ChangesetRegister
        changesets = ChangesetRegister()
        assert len(changesets), "No changesets found in model."
        for id in changesets:
            assert id in res, "Didn't find changeset id '%s' in: %s" % (id, res)

    def test_15_get_changeset(self):
        from ckan.model.changeset import ChangesetRegister
        changesets = ChangesetRegister()
        assert len(changesets), "No changesets found in model."
        for id in changesets:
            offset = self.offset('/rest/changeset/%s' % id)
            res = self.app.get(offset, status=[200])
            changeset_data = self.data_from_res(res)
            assert 'id' in changeset_data, "No 'id' in changeset data: %s" % changeset_data
            assert 'meta' in changeset_data, "No 'meta' in changeset data: %s" % changeset_data
            assert 'changes' in changeset_data, "No 'changes' in changeset data: %s" % changeset_data

    def test_15_get_changeset_404(self):
        changeset_id = "xxxxxxxxxxxxxxxxxxxxxxxxxx"
        offset = self.offset('/rest/changeset/%s' % changeset_id)
        res = self.app.get(offset, status=404)
        model.Session.remove()

    def test_16_list_licenses(self):
        from ckan.model.license import LicenseRegister
        register = LicenseRegister()
        assert len(register), "No changesets found in model."
        offset = self.offset('/rest/licenses')
        res = self.app.get(offset, status=[200])
        licenses_data = self.data_from_res(res)
        assert len(licenses_data) == len(register), (len(licenses_data), len(register))
        for license_data in licenses_data:
            id = license_data['id']
            license = register[id]
            assert license['title'] == license.title
            assert license['url'] == license.url


# Note well, relationships are actually part of the Model API.
class RelationshipsApiTestCase(ApiControllerTestCase):

    @classmethod
    def setup_class(self):
        CreateTestData.create()
        self.user = self.create_user(name=u'barry')
        self.extra_environ={ 'Authorization' : str(self.user.apikey) }
        self.comment = u'Comment umlaut: \xfc.'

    @classmethod
    def teardown_class(self):
        model.Session.remove()
        model.repo.rebuild_db()
        model.Session.remove()

    def teardown(self):
        for relationship in self.anna.get_relationships():
            relationship.purge()
        model.Session.commit()
        relationships = self.anna.get_relationships()
        assert relationships == [], "There are still some relationships: %s" % relationships

    def test_01_create_and_read_relationship(self):
        # check anna has no existing relationships
        assert not self.anna.get_relationships()
        assert self.get_relationships(package1_name='annakarenina') == []
        assert self.get_relationships(package1_name='annakarenina',
                                       package2_name='warandpeace') == []
        assert self.get_relationships(package1_name='annakarenina',
                                       type='child_of',
                                       package2_name='warandpeace') == 404
        assert self.get_relationships_via_package('annakarenina') == []

        # Create a relationship.
        self.create_annakarenina_parent_of_war_and_peace()

        # Check package relationship register.
        rels = self.get_relationships(package1_name='annakarenina')
        assert len(rels) == 1
        self.check_relationship_dict(rels[0],
               'annakarenina', 'parent_of', 'warandpeace', self.comment)

        # Todo: Name this?
        # Check '/api/VER/rest/package/annakarenina/relationships/warandpeace'
        rels = self.get_relationships(package1_name='annakarenina',
                                       package2_name='warandpeace')
        assert len(rels) == 1
        self.check_relationship_dict(rels[0],
               'annakarenina', 'parent_of', 'warandpeace', self.comment)

        # Todo: Name this?
        # check '/api/VER/rest/package/annakarenina/parent_of/warandpeace'
        rels = self.get_relationships(package1_name='annakarenina',
                                       type='parent_of',
                                       package2_name='warandpeace')
        assert len(rels) == 1
        self.check_relationship_dict(rels[0],
               'annakarenina', 'parent_of', 'warandpeace', self.comment)

        # same checks in reverse direction
        rels = self.get_relationships(package1_name='warandpeace')
        assert len(rels) == 1
        self.check_relationship_dict(rels[0],
               'warandpeace', 'child_of', 'annakarenina', self.comment)

        rels = self.get_relationships(package1_name='warandpeace',
                                       package2_name='annakarenina')
        assert len(rels) == 1
        self.check_relationship_dict(rels[0],
               'warandpeace', 'child_of', 'annakarenina', self.comment)

        rels = self.get_relationships(package1_name='warandpeace',
                                       type='child_of',
                                      package2_name='annakarenina')
        assert len(rels) == 1
        self.check_relationship_dict(rels[0],
               'warandpeace', 'child_of', 'annakarenina', self.comment)

        # Check package entity relationships.
        rels = self.get_relationships_via_package('annakarenina')
        assert len(rels) == 1
        self.check_relationship_dict(rels[0],
               'annakarenina', 'parent_of', 'warandpeace', self.comment)
        
    def test_03_update_relationship(self):
        # Create a relationship.
        self.create_annakarenina_parent_of_war_and_peace()

        # Check the relationship before update.
        self.check_relationships_rest('warandpeace', 'annakarenina',
                                      [{'type': 'child_of',
                                        'comment': self.comment}])

        # Update the relationship.
        new_comment = u'New comment.'
        self.update_annakarenina_parent_of_war_and_peace(comment=new_comment)

        # Check the relationship after update.
        self.check_relationships_rest('warandpeace', 'annakarenina', [{'type': 'child_of', 'comment': new_comment}])

        # Repeat update with same values, to check it remains the same?

        # Update the relationship.
        new_comment = u'New comment.'
        self.update_annakarenina_parent_of_war_and_peace(comment=new_comment)

        # Check the relationship after update.
        self.check_relationships_rest('warandpeace', 'annakarenina', [{'type': 'child_of', 'comment': new_comment}])

    def test_05_delete_relationship(self):
        self.create_annakarenina_parent_of_war_and_peace()
        self.update_annakarenina_parent_of_war_and_peace()
        expected = [ {'type': 'child_of', 'comment': u'New comment.'} ]
        self.check_relationships_rest('warandpeace', 'annakarenina', expected)

        self.delete_annakarenina_parent_of_war_and_peace()

        expected = []
        self.check_relationships_rest('warandpeace', 'annakarenina', expected)

    def create_annakarenina_parent_of_war_and_peace(self):
        # Create package relationship.
        # Todo: Redesign this in a RESTful style, so that a relationship is 
        # created by posting a relationship to a relationship **register**.
        offset = self.offset('/rest/package/annakarenina/parent_of/warandpeace')
        postparams = '%s=1' % self.dumps({'comment':self.comment})
        res = self.app.post(offset, params=postparams, status=[200],
                            extra_environ=self.extra_environ)
        # Check the model, directly.
        rels = self.anna.get_relationships()
        assert len(rels) == 1, rels
        assert rels[0].type == 'child_of'
        assert rels[0].subject.name == 'warandpeace'
        assert rels[0].object.name == 'annakarenina'

    def update_annakarenina_parent_of_war_and_peace(self, comment=u'New comment.'):
        offset = self.offset('/rest/package/annakarenina/parent_of/warandpeace')
        postparams = '%s=1' % self.dumps({'comment':comment})
        res = self.app.post(offset, params=postparams, status=[200], extra_environ=self.extra_environ)
        return res

    def delete_annakarenina_parent_of_war_and_peace(self):
        offset = self.offset('/rest/package/annakarenina/parent_of/warandpeace')
        res = self.app.delete(offset, status=[200], extra_environ=self.extra_environ)
        return res

    def get_relationships(self, package1_name=u'annakarenina', type='relationships', package2_name=None):
        package1_ref = self.package_ref_from_name(package1_name)
        if not package2_name:
            offset = self.offset('/rest/package/%s/%s' % (package1_ref, type))
        else:
            package2_ref = self.package_ref_from_name(package2_name)
            offset = self.offset('/rest/package/%s/%s/%s' % (
                str(package1_ref), type, str(package2_ref)))
        allowable_statuses = [200]
        if type:
            allowable_statuses.append(404)
        res = self.app.get(offset, status=allowable_statuses)
        if res.status == 200:
            res_dict = self.data_from_res(res) if res.body else []
            return res_dict
        else:
            return 404

    def get_relationships_via_package(self, package1_name):
        offset = self.offset('/rest/package/%s' % (str(package1_name)))
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        return res_dict['relationships']

    def assert_len_relationships(self, relationships, expected_relationships):
        len_relationships = len(relationships)
        len_expected_relationships = len(expected_relationships)
        if len_relationships != len_expected_relationships:
            msg = 'Found %i relationships, ' % len_relationships
            msg += 'but expected %i.' % len_expected_relationships
            if len_relationships:
                msg += ' Found: '
                for r in relationships:
                    msg += '%s %s %s; ' % r['subject'], r['type'], r['object']
                msg += '.'
            raise Exception, msg

    def check_relationships_rest(self, pkg1_name, pkg2_name=None,
                                 expected_relationships=[]):
        rels = self.get_relationships(package1_name=pkg1_name,
                                      package2_name=pkg2_name)
        self.assert_len_relationships(rels, expected_relationships) 
        for rel in rels:
            the_expected_rel = None
            for expected_rel in expected_relationships:
                if expected_rel['type'] == rel['type'] and \
                   (pkg2_name or expected_rel['object'] == pkg2_name):
                    the_expected_rel = expected_rel
                    break
            if not the_expected_rel:
                raise Exception('Unexpected relationship: %s %s %s' %
                                (rel['subject'], rel['type'], rel['object']))
            for field in ('subject', 'object', 'type', 'comment'):
                if the_expected_rel.has_key(field):
                    value = rel[field]
                    expected = the_expected_rel[field]
                    assert value == expected, (value, expected, field, rel)

    def check_relationship_dict(self, rel_dict, subject_name, type, object_name, comment):
        subject_ref = self.package_ref_from_name(subject_name)
        object_ref = self.package_ref_from_name(object_name)

        assert rel_dict['subject'] == subject_ref, (rel_dict, subject_ref)
        assert rel_dict['object'] == object_ref, (rel_dict, object_ref)
        assert rel_dict['type'] == type, (rel_dict, type)
        assert rel_dict['comment'] == comment, (rel_dict, comment)

# Todo: Rename to PackageSearchApiTestCase.
class PackageSearchApiTestCase(ApiControllerTestCase):

    @classmethod
    def setup_class(self):
        if not is_search_supported():
            import nose
            raise nose.SkipTest
        indexer = TestSearchIndexer()
        CreateTestData.create()
        self.package_fixture_data = {
            'name' : u'testpkg',
            'title': 'Some Title',
            'url': u'http://blahblahblah.mydomain',
            'resources': [{u'url':u'http://blahblahblah.mydomain',
                           u'format':u'', u'description':''}],
            'tags': ['russion', 'novel'],
            'license_id': u'gpl-3.0',
            'extras': {'national_statistic':'yes',
                       'geographic_coverage':'England, Wales'},
        }
        CreateTestData.create_arbitrary(self.package_fixture_data)
        indexer.index()
        self.base_url = self.offset('/search/package')

    @classmethod
    def teardown_class(self):
        CreateTestData.delete()

    def test_01_uri_q(self):
        offset = self.base_url + '?q=%s' % self.package_fixture_data['name']
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        self.assert_package_search_results(res_dict['results'])
        assert res_dict['count'] == 1, res_dict['count']

    def assert_package_search_results(self, results, names=[u'testpkg']):
        for name in names:
            ref = self.package_ref_from_name(name)
            assert ref in results, (ref, results)

    def package_ref_from_name(self, package_name):
        package = self.get_package_by_name(package_name)
        return self.ref_package(package)

    def test_02_post_q(self):
        offset = self.base_url
        query = {'q':'testpkg'}
        res = self.app.post(offset, params=query, status=200)
        res_dict = self.data_from_res(res)
        self.assert_package_search_results(res_dict['results'])
        assert res_dict['count'] == 1, res_dict['count']

    def test_03_uri_qjson(self):
        query = {'q': self.package_fixture_data['name']}
        json_query = self.dumps(query)
        offset = self.base_url + '?qjson=%s' % json_query
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        self.assert_package_search_results(res_dict['results'])
        assert res_dict['count'] == 1, res_dict['count']

    def test_04_post_qjson(self):
        query = {'q': self.package_fixture_data['name']}
        json_query = self.dumps(query)
        offset = self.base_url
        res = self.app.post(offset, params=json_query, status=200)
        res_dict = self.data_from_res(res)
        self.assert_package_search_results(res_dict['results'])
        assert res_dict['count'] == 1, res_dict['count']

    def test_05_uri_qjson_tags(self):
        query = {'q': 'annakarenina tags:russian tags:tolstoy'}
        json_query = self.dumps(query)
        offset = self.base_url + '?qjson=%s' % json_query
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        self.assert_package_search_results(res_dict['results'], names=[u'annakarenina'])
        assert res_dict['count'] == 1, res_dict
        
    def test_05_uri_qjson_tags_multiple(self):
        query = {'q': 'tags:russian tags:tolstoy'}
        json_query = self.dumps(query)
        offset = self.base_url + '?qjson=%s' % json_query
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        self.assert_package_search_results(res_dict['results'], names=[u'annakarenina'])
        assert res_dict['count'] == 1, res_dict

    def test_06_uri_q_tags(self):
        query = webhelpers.util.html_escape('annakarenina tags:russian tags:tolstoy')
        offset = self.base_url + '?q=%s' % query
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        self.assert_package_search_results(res_dict['results'], names=[u'annakarenina'])
        assert res_dict['count'] == 1, res_dict['count']

    def test_07_uri_qjson_tags(self):
        query = {'q': '', 'tags':['tolstoy']}
        json_query = self.dumps(query)
        offset = self.base_url + '?qjson=%s' % json_query
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        self.assert_package_search_results(res_dict['results'], names=[u'annakarenina'])
        assert res_dict['count'] == 1, res_dict

    def test_07_uri_qjson_tags_multiple(self):
        query = {'q': '', 'tags':['tolstoy', 'russian']}
        json_query = self.dumps(query)
        offset = self.base_url + '?qjson=%s' % json_query
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        self.assert_package_search_results(res_dict['results'], names=[u'annakarenina'])
        assert res_dict['count'] == 1, res_dict

    def test_07_uri_qjson_tags_reverse(self):
        query = {'q': '', 'tags':['russian']}
        json_query = self.dumps(query)
        offset = self.base_url + '?qjson=%s' % json_query
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        self.assert_package_search_results(res_dict['results'], names=[u'annakarenina'])
        assert res_dict['count'] == 2, res_dict

    def test_07_uri_qjson_extras(self):
        query = {"geographic_coverage":"England"}
        json_query = self.dumps(query)
        offset = self.base_url + '?qjson=%s' % json_query
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        self.assert_package_search_results(res_dict['results'])
        assert res_dict['count'] == 1, res_dict

    def test_07_uri_qjson_extras_2(self):
        query = {"national_statistic":"yes"}
        json_query = self.dumps(query)
        offset = self.base_url + '?qjson=%s' % json_query
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        self.assert_package_search_results(res_dict['results'])
        assert res_dict['count'] == 1, res_dict
        
        
    def test_08_all_fields(self):
        rating = model.Rating(user_ip_address=u'123.1.2.3',
                              package=self.anna,
                              rating=3.0)
        model.Session.add(rating)
        model.repo.commit_and_remove()
        
        query = {'q': 'russian', 'all_fields':1}
        json_query = self.dumps(query)
        offset = self.base_url + '?qjson=%s' % json_query
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        assert res_dict['count'] == 2, res_dict
        for rec in res_dict['results']:
            if rec['name'] == 'annakarenina':
                anna_rec = rec
                break
        assert anna_rec['name'] == 'annakarenina', res_dict['results']
        assert anna_rec['title'] == 'A Novel By Tolstoy', anna_rec['title']
        assert anna_rec['license_id'] == u'other-open', anna_rec['license_id']
        assert len(anna_rec['tags']) == 2, anna_rec['tags']
        for expected_tag in ['russian', 'tolstoy']:
            assert expected_tag in anna_rec['tags']
        assert anna_rec['ratings_average'] == 3.0, anna_rec['ratings_average']
        assert anna_rec['ratings_count'] == 1, anna_rec['ratings_count']

    def test_09_just_tags(self):
        offset = self.base_url + '?tags=russian&all_fields=1'
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        assert res_dict['count'] == 2, res_dict

    def test_10_multiple_tags_with_plus(self):
        offset = self.base_url + '?tags=tolstoy+russian&all_fields=1'
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        assert res_dict['count'] == 1, res_dict

    def test_10_multiple_tags_with_ampersand(self):
        offset = self.base_url + '?tags=tolstoy&tags=russian&all_fields=1'
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        assert res_dict['count'] == 1, res_dict

    def test_10_many_tags_with_ampersand(self):
        offset = self.base_url + '?tags=tolstoy&tags=russian&tags=tolstoy'
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        assert res_dict['count'] == 1, res_dict

    def test_11_pagination_limit(self):
        offset = self.base_url + '?all_fields=1&tags=russian&limit=1&order_by=name'
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        assert res_dict['count'] == 2, res_dict
        assert len(res_dict['results']) == 1, res_dict
        assert res_dict['results'][0]['name'] == 'annakarenina', res_dict['results'][0]['name']

    def test_11_pagination_offset_limit(self):
        offset = self.base_url + '?all_fields=1&tags=russian&offset=1&limit=1&order_by=name'
        res = self.app.get(offset, status=200)
        res_dict = self.data_from_res(res)
        assert res_dict['count'] == 2, res_dict
        assert len(res_dict['results']) == 1, res_dict
        assert res_dict['results'][0]['name'] == 'warandpeace', res_dict['results'][0]['name']

    def test_12_search_revision_basic(self):
        offset = self.offset('/search/revision')
        # Check bad request.
        self.app.get(offset, status=400)
        self.app.get(offset+'?since_rev=2010-01-01T00:00:00', status=400)
        self.app.get(offset+'?since_revision=2010-01-01T00:00:00', status=400)
        self.app.get(offset+'?since_id=', status=400)

    def test_12_search_revision_since_rev(self):
        offset = self.offset('/search/revision')
        revs = model.Session.query(model.Revision).all()
        rev_first = revs[-1]
        params = "?since_id=%s" % str(rev_first.id)
        res = self.app.get(offset+params, status=200)
        res_list = self.data_from_res(res)
        assert rev_first.id not in res_list
        for rev in revs[:-1]:
            assert rev.id in res_list, (rev.id, res_list)
        rev_last = revs[0]
        params = "?since_id=%s" % str(rev_last.id)
        res = self.app.get(offset+params, status=200)
        res_list = self.data_from_res(res)
        assert res_list == [], res_list

    def test_12_search_revision_since_time(self):
        offset = self.offset('/search/revision')
        revs = model.Session.query(model.Revision).all()
        # Check since time of first.
        rev_first = revs[-1]
        params = "?since_time=%s" % model.strftimestamp(rev_first.timestamp)
        res = self.app.get(offset+params, status=200)
        res_list = self.data_from_res(res)
        assert rev_first.id not in res_list
        for rev in revs[:-1]:
            assert rev.id in res_list, (rev.id, res_list)
        # Check since time of last.
        rev_last = revs[0]
        params = "?since_time=%s" % model.strftimestamp(rev_last.timestamp)
        res = self.app.get(offset+params, status=200)
        res_list = self.data_from_res(res)
        assert res_list == [], res_list
        # Check bad format.
        params = "?since_time=2010-04-31T23:45"
        self.app.get(offset+params, status=400)

    def test_strftimestamp(self):
        import datetime
        t = datetime.datetime(2012, 3, 4, 5, 6, 7, 890123)
        s = model.strftimestamp(t)
        assert s == "2012-03-04T05:06:07.890123", s

    def test_strptimestamp(self):
        import datetime
        s = "2012-03-04T05:06:07.890123"
        t = model.strptimestamp(s)
        assert t == datetime.datetime(2012, 3, 4, 5, 6, 7, 890123), t


class ResourceSearchApiTestCase(ApiControllerTestCase):

    @classmethod
    def setup_class(self):
        CreateTestData.create()
        self.ab = 'http://site.com/a/b.txt'
        self.cd = 'http://site.com/c/d.txt'
        self.package_fixture_data = {
            'name' : u'testpkg',
            'title': 'Some Title',
            'url': u'http://blahblahblah.mydomain',
            'resources':[
                {'url':self.ab,
                 'description':'This is site ab.',
                 'format':'Excel spreadsheet',
                 'hash':'abc-123'},
                {'url':self.cd,
                 'description':'This is site cd.',
                 'format':'Office spreadsheet',
                 'hash':'qwe-456'},
                ],
            'tags': ['russion', 'novel'],
            'license_id': u'gpl-3.0',
            'extras': {'national_statistic':'yes',
                       'geographic_coverage':'England, Wales'},
        }
        CreateTestData.create_arbitrary(self.package_fixture_data)
        self.base_url = self.offset('/search/resource')

    @classmethod
    def teardown_class(self):
        CreateTestData.delete()

    def assert_urls_in_search_results(self, offset, expected_urls):
        result = self.app.get(offset, status=200)
        result_dict = self.loads(result.body)
        resources = [model.Session.query(model.PackageResource).get(resource_id) for resource_id in result_dict['results']]
        urls = set([resource.url for resource in resources])
        assert urls == set(expected_urls), urls
        

    def test_01_url(self):
        offset = self.base_url + '?url=site'
        self.assert_urls_in_search_results(offset, [self.ab, self.cd])

    def test_02_url_qjson(self):
        query = {'url':'site'}
        json_query = self.dumps(query)
        offset = self.base_url + '?qjson=%s' % json_query
        self.assert_urls_in_search_results(offset, [self.ab, self.cd])

    def test_03_post_qjson(self):
        query = {'url':'site'}
        json_query = self.dumps(query)
        offset = self.base_url
        result = self.app.post(offset, params=json_query, status=200)
        expected_urls = [self.ab, self.cd]
        result_dict = self.loads(result.body)
        resources = [model.Session.query(model.PackageResource).get(resource_id) for resource_id in result_dict['results']]
        urls = set([resource.url for resource in resources])
        assert urls == set(expected_urls), urls

    def test_04_bad_option(self):
        offset = self.base_url + '?random=option'
        result = self.app.get(offset, status=400)

    def test_05_options(self):
        offset = self.base_url + '?url=site&all_fields=1&callback=mycallback'
        result = self.app.get(offset, status=200)
        assert re.match('^mycallback\(.*\);$', result.body), result.body
        assert 'package_id' in result.body, result.body


class QosApiTestCase(ApiControllerTestCase):

    def test_throughput(self):
        if not config.get('ckan.enable_call_timing', None):
            raise SkipTest
        # Create some throughput.
        import datetime
        start = datetime.datetime.now()
        offset = self.offset('/rest/package')
        while datetime.datetime.now() - start < datetime.timedelta(0,10):
            res = self.app.get(offset, status=[200])
        # Check throughput.
        offset = self.offset('/qos/throughput/')
        res = self.app.get(offset, status=[200])
        data = self.data_from_res(res)
        throughput = float(data)
        assert throughput > 1, throughput
 

class MiscApiTestCase(ApiControllerTestCase):

    @classmethod
    def setup_class(self):
        try:
            CreateTestData.delete()
        except:
            pass
        model.repo.init_db()
        model.Session.remove()
        CreateTestData.create()

    @classmethod
    def teardown_class(self):
        model.Session.remove()
        CreateTestData.delete()

    # Todo: Move this method to the Model API?
    def test_0_tag_counts(self):
        offset = self.offset('/tag_counts')
        res = self.app.get(offset, status=200)
        assert '["russian", 2]' in res, res
        assert '["tolstoy", 1]' in res, res


# Tests for Version 1 of the API.
class TestModelApi1(Api1TestCase, ModelApiTestCase):

    def test_06_create_pkg_using_download_url(self):
        test_params = {
            'name':u'testpkg06',
            'download_url':u'testurl',
            }
        offset = self.package_offset()
        postparams = '%s=1' % self.dumps(test_params)
        res = self.app.post(offset, params=postparams, status=[200],
                extra_environ=self.extra_environ)
        model.Session.remove()
        pkg = self.get_package_by_name(test_params['name'])
        assert pkg
        assert pkg.name == test_params['name'], pkg
        assert len(pkg.resources) == 1, pkg.resources
        assert pkg.resources[0].url == test_params['download_url'], pkg.resources[0]

    def test_10_edit_pkg_with_download_url(self):
        test_params = {
            'name':u'testpkg10',
            'download_url':u'testurl',
            }
        rev = model.repo.new_revision()
        pkg = model.Package()
        model.Session.add(pkg)
        pkg.name = test_params['name']
        pkg.download_url = test_params['download_url']
        model.Session.commit()

        pkg = self.get_package_by_name(test_params['name'])
        model.setup_default_user_roles(pkg, [self.user])
        rev = model.repo.new_revision()
        model.repo.commit_and_remove()
        assert self.get_package_by_name(test_params['name'])

        # edit it
        pkg_vals = {'download_url':u'newurl'}
        offset = self.package_offset(test_params['name'])
        postparams = '%s=1' % self.dumps(pkg_vals)
        res = self.app.post(offset, params=postparams, status=[200],
                            extra_environ=self.extra_environ)
        model.Session.remove()
        pkg = model.Session.query(model.Package).filter_by(name=test_params['name']).one()
        assert len(pkg.resources) == 1, pkg.resources
        assert pkg.resources[0].url == pkg_vals['download_url']


class TestRelationshipsApi1(Api1TestCase, RelationshipsApiTestCase): pass
class TestPackageSearchApi1(Api1TestCase, PackageSearchApiTestCase): pass
class TestResourceSearchApi1(ResourceSearchApiTestCase, Api1TestCase): pass
class TestMiscApi1(Api1TestCase, MiscApiTestCase): pass
class TestQosApi1(Api1TestCase, QosApiTestCase): pass

# Tests for Version 2 of the API.
class TestModelApi2(Api2TestCase, ModelApiTestCase): pass
class TestRelationshipsApi2(Api2TestCase, RelationshipsApiTestCase): pass
class TestPackageSearchApi2(Api2TestCase, PackageSearchApiTestCase): pass
class TestResourceSearchApi2(Api2TestCase, ResourceSearchApiTestCase): pass
class TestMiscApi2(Api2TestCase, MiscApiTestCase): pass
class TestQosApi2(Api2TestCase, QosApiTestCase): pass

# Tests for unversioned API.
class TestModelApiUnversioned(ApiUnversionedTestCase, ModelApiTestCase): pass

# Todo: Refactor to run the download_url tests on versioned location too.
#class TestRelationshipsApiUnversioned(RelationshipsApiTestCase, ApiUnversionedTestCase):
#    pass
#
#class TestPackageSearchApiUnversioned(PackageSearchApiTestCase, ApiUnversionedTestCase):
#    pass
#
class TestResourceSearchApiUnversioned(ApiUnversionedTestCase, ResourceSearchApiTestCase):
    pass

#class TestMiscApiUnversioned(MiscApiTestCase, ApiUnversionedTestCase):
#    pass

class TestQosApiUnversioned(ApiUnversionedTestCase, QosApiTestCase): pass

