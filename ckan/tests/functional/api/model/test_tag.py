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
        results = self.loads(res.body)
        assert self.russian.name in results, results
        assert self.tolstoy.name in results, results
        assert self.flexible_tag.name in results, results
    
    def test_entity_get_ok(self):
        offset = self.tag_offset(self.russian.name)
        res = self.app.get(offset, status=self.STATUS_200_OK)
        self.assert_msg_represents_russian(msg=res.body)

    def test_entity_get_ok_flexible_tag(self):
        """
        Asserts that searching for a tag name with spaces and punctuation works.

        The tag name is u'Flexible \u0489!', and both the 'warandpeace'
        and 'annakarenina' packages should be returned.
        """
        offset = self.tag_offset(self.flexible_tag.name)
        res = self.app.get(offset, status=self.STATUS_200_OK)
        self.assert_msg_represents_flexible_tag(msg=res.body)

    def test_entity_get_not_found(self):
        offset = self.tag_offset('doesntexist')
        res = self.app.get(offset, status=404)
        self.assert_json_response(res, 'Not found')

class TestTagsVersion1(Version1TestCase, TagsTestCase): pass
class TestTagsVersion2(Version2TestCase, TagsTestCase): pass
class TestTagsUnversioned(UnversionedTestCase, TagsTestCase): pass
