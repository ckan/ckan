from ckan.tests.functional.api.base import *
from ckan.lib.create_test_data import CreateTestData
from ckan.tests import TestController as ControllerTestCase

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
        model.repo.rebuild_db()

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
        res = self.app.post(offset, params=postparams, status=201,
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
        res = self.app.post(offset, params=postparams, status=[201],
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
        res = self.app.post(offset, params=postparams, status=[201],
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
        res = self.app.post(offset, params=postparams, status=[409],
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
            res = self.app.post(offset, params=postparams, status=[201],
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

        group = model.Group.by_name(self.testgroupvalues['name'])
        assert group
        assert group.state == 'deleted', group.state

        res = self.app.get(offset, status=[403])
        res = self.app.get(offset, status=[200],
                           extra_environ=self.extra_environ)

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


class RelationshipsApiTestCase(ApiTestCase, ControllerTestCase):

    @classmethod
    def setup_class(self):
        CreateTestData.create()
        self.user = self.create_user(name=u'barry')
        self.testsysadmin = model.User.by_name(u'testsysadmin')
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
        assert self.get_relationships(package1_name='annakarenina') == [], self.get_relationships(package1_name='annakarenina')
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
        res = self.app.post(offset, params=postparams, status=[201],
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
        res = self.app.post(offset, params=postparams, status=[201], extra_environ=self.extra_environ)
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
                    msg += '%s %s %s; ' % (r['subject'], r['type'], r['object'])
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
 

# Tests for Version 1 of the API.
class TestModelApi1(Api1TestCase, ModelApiTestCase):

    def test_06_create_pkg_using_download_url(self):
        test_params = {
            'name':u'testpkg06',
            'download_url':u'ftp://ftp.monash.edu.au/pub/nihongo/JMdict.gz',
            }
        offset = self.package_offset()
        postparams = '%s=1' % self.dumps(test_params)
        res = self.app.post(offset, params=postparams, 
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

# Tests for Version 2 of the API.
class TestModelApi2(Api2TestCase, ModelApiTestCase): pass
class TestRelationshipsApi2(Api2TestCase, RelationshipsApiTestCase): pass

# Tests for unversioned API.
class TestModelApiUnversioned(ApiUnversionedTestCase, ModelApiTestCase): pass
class TestRelationshipsApiUnversioned(RelationshipsApiTestCase, ApiUnversionedTestCase): pass

