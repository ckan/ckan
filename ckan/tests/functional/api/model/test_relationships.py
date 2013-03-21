from nose.tools import assert_equal 
from nose.plugins.skip import SkipTest

from ckan import model
from ckan.lib.create_test_data import CreateTestData

from ckan.tests.functional.api.base import BaseModelApiTestCase
from ckan.tests.functional.api.base import Api1TestCase as Version1TestCase 
from ckan.tests.functional.api.base import Api2TestCase as Version2TestCase 

class RelationshipsTestCase(BaseModelApiTestCase):

    @classmethod
    def setup_class(cls):
        CreateTestData.create()
        cls.testsysadmin = model.User.by_name(u'testsysadmin')
        cls.comment = u'Comment umlaut: \xfc.'
        cls.user_name = u'annafan' # created in CreateTestData
        cls.init_extra_environ(cls.user_name)

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()

    def teardown(self):
        relationships = model.Session.query(model.PackageRelationship).all()
        for rel in relationships:
            rel.purge()
        model.repo.commit_and_remove()

    def relationship_offset(self, package_1_name=None,
                            relationship_type=None,
                            package_2_name=None,
                            ):
        assert package_1_name
        package_1_ref = self.package_ref_from_name(package_1_name)
        if package_2_name is None:
            if not relationship_type:
                return self.offset('/rest/dataset/%s/relationships' % \
                                   package_1_ref)
            else:
                return self.offset('/rest/dataset/%s/%s' %
                                   (package_1_ref, relationship_type))
        else:
            package_2_ref = self.package_ref_from_name(package_2_name)
            if not relationship_type:
                return self.offset('/rest/dataset/%s/relationships/%s' % \
                                   (package_1_ref, package_2_ref))
            else:
                return self.offset('/rest/dataset/%s/%s/%s' % \
                                   (package_1_ref,
                                    relationship_type,
                                    package_2_ref))

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
        
    def test_02_create_relationship_way_2(self):
        # Create a relationship using 2nd way
        self.create_annakarenina_parent_of_war_and_peace(way=2)

    def test_02_create_relationship_way_3(self):
        # Create a relationship using 3rd way
        self.create_annakarenina_parent_of_war_and_peace(way=3)

    def test_02_create_relationship_way_4(self):
        # Create a relationship using 4th way
        self.create_annakarenina_parent_of_war_and_peace(way=4)

    def test_02_create_link_relationship(self):
        offset = self.relationship_offset('annakarenina')
        data = {'type': 'links_to',
                'object': 'warandpeace',
                'comment':self.comment}
        postparams = '%s=1' % self.dumps(data)
        res = self.app.post(offset, params=postparams, status=[201],
                            extra_environ=self.extra_environ)
        # Check the response
        rel = self.loads(res.body)
        assert_equal(rel['type'], 'links_to')
        assert_equal(rel['subject'], self.ref_package(self.anna))
        assert_equal(rel['object'], self.ref_package(self.war))

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

    def test_create_relationship_unknown(self):
        offset = self.relationship_offset('annakarenina', 'unheard_of_type', 'warandpeace')
        postparams = '%s=1' % self.dumps({'comment':self.comment})
        res = self.app.post(offset, params=postparams, status=[409],
                            extra_environ=self.extra_environ)
        # error message is wrong - ends up in package_create,
        # but at least there is an error

    def create_annakarenina_parent_of_war_and_peace(self, way=1):
        # Create package relationship.
        # More than one 'way' to create a package.
        # Todo: Redesign this in a RESTful style, so that a relationship is 
        # created by posting a relationship to a relationship **register**.
        assert way in (1, 2, 3, 4)
        if way == 1:
            # Dataset Relationship Entity - old way (deprecated)
            offset = self.relationship_offset('annakarenina', 'parent_of', 'warandpeace')
            data = {'comment':self.comment}
        elif way == 2:
            # Dataset Relationships Register 1
            offset = self.relationship_offset('annakarenina', 'relationships')
            data = {'type': 'parent_of',
                    'object': 'warandpeace',
                    'comment':self.comment}
        elif way == 3:
            # Dataset Relationships Register 2
            offset = self.relationship_offset('annakarenina', 'parent_of')
            data = {'object': 'warandpeace',
                    'comment':self.comment}
        elif way == 4:
            # Dataset Relationships Register 3
            offset = self.relationship_offset('annakarenina', 'relationships', 'warandpeace')
            data = {'type': 'parent_of',
                    'comment':self.comment}
        postparams = '%s=1' % self.dumps(data)
        res = self.app.post(offset, params=postparams, status=[201],
                            extra_environ=self.extra_environ)
        # Check the response
        rel = self.loads(res.body)
        assert_equal(rel['type'], 'child_of')
        assert_equal(rel['subject'], self.ref_package(self.war))
        assert_equal(rel['object'], self.ref_package(self.anna))
        
        # Check the model, directly.
        rels = self.anna.get_relationships()
        assert len(rels) == 1, rels
        assert rels[0].type == 'child_of'
        assert rels[0].subject.name == 'warandpeace'
        assert rels[0].object.name == 'annakarenina'

    def update_annakarenina_parent_of_war_and_peace(self, comment=u'New comment.'):
        offset = self.relationship_offset('annakarenina', 'parent_of', 'warandpeace')
        postparams = '%s=1' % self.dumps({'comment':comment})
        res = self.app.put(offset, params=postparams, status=[200], extra_environ=self.extra_environ)
        # Check the response
        rel = self.loads(res.body)
        assert_equal(rel['type'], 'child_of')
        assert_equal(rel['subject'], self.ref_package(self.war))
        assert_equal(rel['object'], self.ref_package(self.anna))

        # Check the model, directly (normalised to 'child_of')
        rels = self.anna.get_relationships()
        assert len(rels) == 1, rels
        assert rels[0].type == 'child_of'
        assert rels[0].subject.name == 'warandpeace'
        assert rels[0].object.name == 'annakarenina'
        return res

    def test_update_relationship_incorrectly(self):
        self.create_annakarenina_parent_of_war_and_peace()
        offset = self.relationship_offset('annakarenina', 'parent_of', 'warandpeace')
        postparams = '%s=1' % self.dumps({'type': 'cat', 'object': 'Matilda', 'comment': 'Tabby'})
        # Should only be able to change the comment.
        # Todo: validate this properly and return an error
        # Currently it just ignores the changed type and subject/object
        res = self.app.put(offset, params=postparams, status=[200],
                           extra_environ=self.extra_environ)
        print res.body
        assert 'cat' not in res.body
        assert 'Matilda' not in res.body
        assert 'Tabby' in res.body

    def delete_annakarenina_parent_of_war_and_peace(self):
        offset = self.relationship_offset('annakarenina', 'parent_of', 'warandpeace')
        res = self.app.delete(offset, status=[200], extra_environ=self.extra_environ)
        assert not res.body, res.body

    def get_relationships(self, package1_name=u'annakarenina', type='relationships', package2_name=None):
        offset = self.relationship_offset(package1_name, type, package2_name)
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
        offset = self.package_offset(package1_name)
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

class TestRelationshipsVersion1(Version1TestCase, RelationshipsTestCase): pass
class TestRelationshipsVersion2(Version2TestCase, RelationshipsTestCase): pass
