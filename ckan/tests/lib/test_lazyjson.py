from nose.tools import assert_equal

from ckan.lib.lazyjson import LazyJSONObject
import ckan.lib.helpers as h


class TestLazyJson(object):
    def test_dump_without_necessarily_going_via_a_dict(self):
        json_string = '{"title": "test_2"}'
        lazy_json_obj = LazyJSONObject(json_string)
        dumped = h.json.dumps(
            lazy_json_obj,
            for_json=True)
        assert_equal(dumped, json_string)

    def test_dump_without_needing_to_go_via_a_dict(self):
        json_string = '"invalid" JSON to [{}] ensure it doesnt become a dict'
        lazy_json_obj = LazyJSONObject(json_string)
        dumped = h.json.dumps(
            lazy_json_obj,
            for_json=True)
        assert_equal(dumped, json_string)

    def test_treat_like_a_dict(self):
        json_string = '{"title": "test_2"}'
        lazy_json_obj = LazyJSONObject(json_string)
        assert_equal(lazy_json_obj.keys(), ['title'])
        assert_equal(len(lazy_json_obj), 1)
