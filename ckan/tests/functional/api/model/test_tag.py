import copy

from nose.tools import assert_equal 

from ckan.tests.functional.api.base import BaseModelApiTestCase
from ckan.tests.functional.api.base import Api1TestCase as Version1TestCase 
from ckan.tests.functional.api.base import Api2TestCase as Version2TestCase 
from ckan.tests.functional.api.base import ApiUnversionedTestCase as UnversionedTestCase 

class TagsTestCase(BaseModelApiTestCase):

    commit_changesets = False
    reuse_common_fixtures = True
    
    def test_register_get_ok(self):
        offset = self.tag_offset()
        res = self.app.get(offset, status=self.STATUS_200_OK)
        assert self.russian.name in res, res
        assert self.tolstoy.name in res, res
    
    def test_entity_get_ok(self):
        offset = self.tag_offset(self.russian.name)
        res = self.app.get(offset, status=self.STATUS_200_OK)
        self.assert_msg_represents_russian(msg=res.body)


class TestTagsVersion1(Version1TestCase, TagsTestCase): pass
class TestTagsVersion2(Version2TestCase, TagsTestCase): pass
class TestTagsUnversioned(UnversionedTestCase, TagsTestCase): pass
