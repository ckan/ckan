import copy

from ckan import model
from ckan.lib.create_test_data import CreateTestData

from nose.tools import assert_equal

from ckan.tests.functional.api.base import BaseModelApiTestCase
from ckan.tests.functional.api.base import Api1TestCase as Version1TestCase
from ckan.tests.functional.api.base import Api2TestCase as Version2TestCase


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
