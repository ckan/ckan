import copy

from ckan import model
from ckan.lib.create_test_data import CreateTestData

from nose.tools import assert_equal
import paste
import pylons.test

from ckan.tests.functional.api.base import BaseModelApiTestCase
from ckan.tests.functional.api.base import Api1TestCase as Version1TestCase
from ckan.tests.functional.api.base import Api2TestCase as Version2TestCase
import ckan.tests as tests


class GroupsTestCase(BaseModelApiTestCase):

    @classmethod
    def setup_class(cls):
        CreateTestData.create()
        cls.user_name = u'russianfan' # created in CreateTestData
        cls.init_extra_environ(cls.user_name)

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()

    def teardown(self):
        self.purge_group_by_name(self.testgroupvalues['name'])

    def test_register_get_ok(self):
        offset = self.group_offset()
        res = self.app.get(offset, status=self.STATUS_200_OK)
        assert self.ref_group(self.roger) in res, res
        assert self.ref_group(self.david) in res, res

    def test_register_post_ok(self):
        data = self.testgroupvalues
        postparams = '%s=1' % self.dumps(data)
        offset = self.group_offset()
        res = self.app.post(offset, params=postparams,
                            status=self.STATUS_201_CREATED,
                            extra_environ=self.extra_environ)
        # check group object
        group = self.get_group_by_name(self.testgroupvalues['name'])
        assert group
        assert group.title == self.testgroupvalues['title'], group
        assert group.description == self.testgroupvalues['description'], group
        pkg_ids = [member.table_id for member in group.member_all]
        pkgs = model.Session.query(model.Package).filter(model.Package.id.in_(pkg_ids)).all()
        pkg_names = [pkg.name for pkg in pkgs]

        assert set(pkg_names) == set(('annakarenina', 'warandpeace')), pkg_names

        # check register updated
        res = self.app.get(offset, status=self.STATUS_200_OK)
        data = self.loads(res.body)
        assert isinstance(data, list), data
        assert self._ref_group(group) in data, data

        # check entity
        offset = self.group_offset(self.testgroupvalues['name'])
        res = self.app.get(offset, status=self.STATUS_200_OK)
        group = self.loads(res.body)
        expected_group = copy.deepcopy(self.testgroupvalues)
        expected_group['packages'] = \
               sorted([self.ref_package(self.get_package_by_name(pkg_name)) \
                for pkg_name in expected_group['packages']])
        for expected_key, expected_value in expected_group.items():
            assert_equal(group.get(expected_key), expected_value)

        # Test Group Register Post 409 (conflict - create duplicate group).
        offset = self.group_offset()
        postparams = '%s=1' % self.dumps(self.testgroupvalues)
        res = self.app.post(offset, params=postparams,
                            status=self.STATUS_409_CONFLICT,
                            extra_environ=self.extra_environ)
        self.assert_json_response(res, 'Group name already exists')

    def test_entity_get_ok(self):
        offset = self.group_offset(self.roger.name)
        res = self.app.get(offset, status=self.STATUS_200_OK)

        self.assert_msg_represents_roger(msg=res.body)
        assert self.package_ref_from_name('annakarenina') in res, res
        assert self.group_ref_from_name('roger') in res, res
        assert not self.package_ref_from_name('warandpeace') in res, res

    def test_entity_get_then_post(self):
        # (ticket 662) Ensure an entity you 'get' from a register can be
        # returned by posting it back
        offset = self.group_offset(self.david.name)
        res = self.app.get(offset, status=self.STATUS_200_OK)
        data = self.loads(res.body)
        postparams = '%s=1' % self.dumps(data)
        res = self.app.post(offset, params=postparams,
                            status=self.STATUS_200_OK,
                            extra_environ=self.admin_extra_environ)
        res = self.set_env(self.extra_environ)

    def test_05_get_group_entity_not_found(self):
        offset = self.offset('/rest/group/22222')
        res = self.app.get(offset, status=404)
        self.assert_json_response(res, 'Not found')

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
        assert len(group.member_all) == 3, group.member_all
        user = model.User.by_name(self.user_name)
        model.setup_default_user_roles(group, [user])

        # edit it
        group_vals = {'name':u'somethingnew', 'title':u'newtesttitle',
                      'packages':[u'annakarenina']}
        offset = self.group_offset(self.testgroupvalues['name'])
        postparams = '%s=1' % self.dumps(group_vals)
        res = self.app.post(offset, params=postparams, status=[200],
                            extra_environ=self.extra_environ)
        model.Session.remove()
        group = model.Session.query(model.Group).filter_by(name=group_vals['name']).one()
        package = model.Session.query(model.Package).filter_by(name='annakarenina').one()
        assert group.name == group_vals['name']
        assert group.title == group_vals['title']
        assert len(group.member_all) == 3, group.member_all
        assert len([mem for mem in group.member_all if mem.state == 'active']) == 2, group.member_all
        for mem in group.member_all:
            if mem.state == 'active' and mem.capacity == 'package':
                assert mem.table_id == package.id

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
        offset = self.group_offset(self.testgroupvalues['name'])
        postparams = '%s=1' % self.dumps(group_vals)
        res = self.app.post(offset, params=postparams, status=[409],
                            extra_environ=self.admin_extra_environ)
        self.assert_json_response(res, 'Group name already exists')
        res = self.set_env(self.extra_environ)

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
        offset = self.group_offset(self.testgroupvalues['name'])
        res = self.app.delete(offset, status=[200],
                extra_environ=self.admin_extra_environ)

        res = self.set_env(self.extra_environ)

        group = model.Group.by_name(self.testgroupvalues['name'])
        assert group
        assert group.state == 'deleted', group.state

        # Anyone can see groups especially sysadmins
        # maybe we want to do something different with
        # deleted groups but that would be a new requirement
        #res = self.app.get(offset, status=[403])
        #self.assert_json_response(res, 'Access denied')
        res = self.app.get(offset, status=[200],
                           extra_environ=self.admin_extra_environ)
        res = self.set_env(self.extra_environ)

    def test_12_get_group_404(self):
        # Test Package Entity Get 404.
        assert not model.Session.query(model.Group).filter_by(name=self.testgroupvalues['name']).count()
        offset = self.group_offset(self.testgroupvalues['name'])
        res = self.app.get(offset, status=404)
        self.assert_json_response(res, 'Not found')

    def test_13_delete_group_404(self):
        # Test Packages Entity Delete 404.
        assert not model.Session.query(model.Group).filter_by(name=self.testgroupvalues['name']).count()
        offset = self.group_offset(self.testgroupvalues['name'])
        res = self.app.delete(offset, status=[404],
                              extra_environ=self.extra_environ)
        self.assert_json_response(res, 'not found')


class TestGroupsVersion1(Version1TestCase, GroupsTestCase): pass
class TestGroupsVersion2(Version2TestCase, GroupsTestCase): pass


class TestGroupPurging(object):
    '''Tests for the group_purge API.

    '''
    @classmethod
    def setup_class(cls):
        cls.app = paste.fixture.TestApp(pylons.test.pylonsapp)

        # Make a sysadmin user.
        cls.sysadmin = model.User(name='test_sysadmin', sysadmin=True)
        model.Session.add(cls.sysadmin)
        model.Session.commit()
        model.Session.remove()

        # A package that will be added to our test groups.
        cls.package = tests.call_action_api(cls.app, 'package_create',
                                            name='group_package',
                                            apikey=cls.sysadmin.apikey)

        # A user who will not be a member of our test groups.
        cls.group_visitor = tests.call_action_api(cls.app, 'user_create',
                                                  name='non_member',
                                                  email='blah',
                                                  password='farm',
                                                  apikey=cls.sysadmin.apikey)

        # A user who will become a member of our test groups.
        cls.group_member = tests.call_action_api(cls.app, 'user_create',
                                                 name='member',
                                                 email='blah',
                                                 password='farm',
                                                 apikey=cls.sysadmin.apikey)

        # A user who will become an editor of our test groups.
        cls.group_editor = tests.call_action_api(cls.app, 'user_create',
                                                 name='editor',
                                                 email='blah',
                                                 password='farm',
                                                 apikey=cls.sysadmin.apikey)

        # A user who will become an admin of our test groups.
        cls.group_admin = tests.call_action_api(cls.app, 'user_create',
                                                name='admin',
                                                email='blah',
                                                password='farm',
                                                apikey=cls.sysadmin.apikey)

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()

    def _group_create(self, group_name):
        '''Make a group with a user and a dataset.'''

        # Make a group with a user.
        group = tests.call_action_api(self.app, 'group_create',
                                      apikey=self.sysadmin.apikey,
                                      name=group_name,
                                      users=[
                                          {'name': self.group_member['name'],
                                           'capacity': 'member',
                                           },
                                          {'name': self.group_editor['name'],
                                           'capacity': 'editor',
                                           },
                                          {'name': self.group_admin['name'],
                                           'capacity': 'admin',
                                           }],
                                      packages=[
                                          {'id': self.package['name']}],
                                      )

        # Let's just make sure that worked.
        package = tests.call_action_api(self.app, 'package_show',
                                        id=self.package['id'])
        assert group['name'] in [group_['name']
                                 for group_ in package['groups']]
        group = tests.call_action_api(self.app, 'group_show', id=group['id'])
        assert self.package['name'] in [package_['name'] for package_ in
                                        group['packages']]
        assert self.group_visitor['name'] not in [user['name']
                                                  for user in group['users']]
        assert self.group_member['name'] in [user['name']
                                             for user in group['users']
                                             if user['capacity'] == 'member']
        assert self.group_editor['name'] in [user['name']
                                             for user in group['users']
                                             if user['capacity'] == 'editor']
        assert self.group_admin['name'] in [user['name']
                                            for user in group['users']
                                            if user['capacity'] == 'admin']

        return group

    def _test_group_purge(self, group_name, by_id):
        '''Create a group with the given name, and test purging it.

        :param name: the name of the group to create and purge
        :param by_id: if True, pass the group's id to group_purge,
            otherwise pass its name
        :type by_id: boolean

        '''
        group = self._group_create(group_name)

        # Purge the group.
        if by_id:
            result = tests.call_action_api(self.app, 'group_purge',
                                           apikey=self.sysadmin.apikey,
                                           id=group['id'],
                                           )
        else:
            result = tests.call_action_api(self.app, 'group_purge',
                                           apikey=self.sysadmin.apikey,
                                           id=group['name'],
                                           )
        assert result is None

        # Now trying to show the group should give a 404.
        result = tests.call_action_api(self.app, 'group_show',
                                       id=group_name, status=404)
        assert result == {'__type': 'Not Found Error', 'message': 'Not found'}

        # The group should not appear in group_list.
        assert group_name not in tests.call_action_api(self.app, 'group_list')

        # The package should no longer belong to the group.
        package = tests.call_action_api(self.app, 'package_show',
                                        id=self.package['name'])
        assert group['name'] not in [group_['name'] for group_
                                     in package['groups']]

        # TODO: Also want to assert that user is not in group anymore,
        # but how to get a user's groups?

        # It should be possible to create a new group with the same name as the
        # purged one (you would not be able to do this if you had merely
        # deleted the original group).
        new_group = tests.call_action_api(self.app, 'group_create',
                                          name=group_name,
                                          apikey=self.sysadmin.apikey,
                                          )
        assert new_group['name'] == group_name

        # TODO: Should we do a model-level check, to check that the group is
        # really purged?

    def test_group_purge_by_name(self):
        self._test_group_purge('group-to-be-purged', by_id=False)

    def test_group_purge_by_id(self):
        self._test_group_purge('group-to-be-purged-2', by_id=True)

    def test_group_purge_with_invalid_id(self):

        for name in ('foo', 'invalid name', None, ''):
            # Try to purge a group, but pass an invalid name.
            result = tests.call_action_api(self.app, 'group_purge',
                                           apikey=self.sysadmin.apikey,
                                           id=name,
                                           status=404,
                                           )
            assert result == {'__type': 'Not Found Error',
                              'message': 'Not found: Group was not found'}

    def test_group_purge_with_missing_id(self):
        result = tests.call_action_api(self.app, 'group_purge',
                                       apikey=self.sysadmin.apikey,
                                       status=409,
                                       )
        assert result == {'__type': 'Validation Error',
                          'id': ['Missing value']}

    def test_visitors_cannot_purge_groups(self):
        '''Visitors (who aren't logged in) should not be authorized to purge
        groups.

        '''
        group = self._group_create('group-to-be-purged-3')

        # Try to purge the group without an API key.
        result = tests.call_action_api(self.app, 'group_purge',
                                       id=group['id'],
                                       status=403,
                                       )
        assert result == {'__type': 'Authorization Error',
                          'message': 'Access denied'}

    def test_users_cannot_purge_groups(self):
        '''Users who are not members of a group should not be authorized to
        purge the group.

        '''
        group = self._group_create('group-to-be-purged-4')

        # Try to purge the group with a non-member's API key.
        result = tests.call_action_api(self.app, 'group_purge',
                                       id=group['id'],
                                       apikey=self.group_visitor['apikey'],
                                       status=403,
                                       )
        assert result == {'__type': 'Authorization Error',
                          'message': 'Access denied'}

    def test_members_cannot_purge_groups(self):
        '''Members of a group should not be authorized to purge the group.

        '''
        group = self._group_create('group-to-be-purged-5')

        # Try to purge the group with a group member's API key.
        result = tests.call_action_api(self.app, 'group_purge',
                                       id=group['id'],
                                       apikey=self.group_member['apikey'],
                                       status=403,
                                       )
        assert result == {'__type': 'Authorization Error',
                          'message': 'Access denied'}

    def test_editors_cannot_purge_groups(self):
        '''Editors of a group should not be authorized to purge the group.

        '''
        group = self._group_create('group-to-be-purged-6')

        # Try to purge the group with an editor's API key.
        result = tests.call_action_api(self.app, 'group_purge',
                                       id=group['id'],
                                       apikey=self.group_editor['apikey'],
                                       status=403,
                                       )
        assert result == {'__type': 'Authorization Error',
                          'message': 'Access denied'}

    def test_admins_cannot_purge_groups(self):
        '''Admins of a group should not be authorized to purge the group.

        '''
        group = self._group_create('group-to-be-purged-7')

        # Try to purge the group with an admin's API key.
        result = tests.call_action_api(self.app, 'group_purge',
                                       id=group['id'],
                                       apikey=self.group_admin['apikey'],
                                       status=403,
                                       )
        assert result == {'__type': 'Authorization Error',
                          'message': 'Access denied'}
