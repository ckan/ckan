import copy

from nose.tools import assert_equal 

from ckan.tests.functional.api.base import BaseModelApiTestCase
from ckan.tests.functional.api.base import Api1TestCase as Version1TestCase 
from ckan.tests.functional.api.base import Api2TestCase as Version2TestCase 
from ckan.tests.functional.api.base import ApiUnversionedTestCase as UnversionedTestCase 

class GroupsTestCase(BaseModelApiTestCase):

    commit_changesets = False
    reuse_common_fixtures = True
    user_name = u'russianfan'
    
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
                            status=self.STATUS_200_OK,
                            extra_environ=self.extra_environ)
        # check group object
        group = self.get_group_by_name(self.testgroupvalues['name'])
        assert group

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
               [self.ref_package(self.get_package_by_name(pkg_name)) \
                for pkg_name in expected_group['packages']]
        for expected_key, expected_value in expected_group.items():
            assert_equal(group.get(expected_key), expected_value)

        # Test Group Register Post 409 (conflict - create duplicate group).
        offset = self.group_offset()
        postparams = '%s=1' % self.dumps(self.testgroupvalues)
        res = self.app.post(offset, params=postparams,
                            status=self.STATUS_409_CONFLICT,
                            extra_environ=self.extra_environ)
    
    def test_entity_get_ok(self):
        offset = self.group_offset(self.roger.name)
        res = self.app.get(offset, status=self.STATUS_200_OK)
        self.assert_msg_represents_roger(msg=res.body)

    def test_entity_get_then_post(self):
        # (ticket 662) Ensure an entity you 'get' from a register can be
        # returned by posting it back
        offset = self.group_offset(self.david.name)
        res = self.app.get(offset, status=self.STATUS_200_OK)
        data = self.loads(res.body)
        postparams = '%s=1' % self.dumps(data)
        res = self.app.post(offset, params=postparams,
                            status=self.STATUS_200_OK,
                            extra_environ=self.extra_environ)

class TestGroupsVersion1(Version1TestCase, GroupsTestCase): pass
class TestGroupsVersion2(Version2TestCase, GroupsTestCase): pass
class TestGroupsUnversioned(UnversionedTestCase, GroupsTestCase): pass
