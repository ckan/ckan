# encoding: utf-8

import json
import pytest
import ckan.model as model
from ckan.lib.create_test_data import CreateTestData
from ckan.tests.legacy import StatusCodes


class TestAction(object):
    @pytest.fixture(autouse=True)
    def setup_class(self, clean_db, clean_index):
        CreateTestData.create()
        self.sysadmin_user = model.User.get("testsysadmin")
        CreateTestData.make_some_vocab_tags()

    def test_08_user_create_not_authorized(self, app):
        res = app.post(
            "/api/action/user_create",
            json={"name": "test_create_from_action_api", "password": "testpass"},
            status=StatusCodes.STATUS_403_ACCESS_DENIED,
        )
        res_obj = json.loads(res.body)
        assert "/api/3/action/help_show?name=user_create" in res_obj["help"]
        assert res_obj["success"] is False
        assert res_obj["error"]["__type"] == "Authorization Error"

    def test_09_user_create(self, app):
        user_dict = {
            "name": "test_create_from_action_api",
            "about": "Just a test user",
            "email": "me@test.org",
            "password": "testpass",
        }

        res = app.post(
            "/api/action/user_create",
            json=user_dict,
            extra_environ={"Authorization": str(self.sysadmin_user.apikey)},
        )
        res_obj = json.loads(res.body)
        assert "/api/3/action/help_show?name=user_create" in res_obj["help"]
        assert res_obj["success"] == True
        result = res_obj["result"]
        assert result["name"] == user_dict["name"]
        assert result["about"] == user_dict["about"]
        assert "apikey" in result
        assert "created" in result
        assert "display_name" in result
        assert "number_created_packages" in result
        assert not "password" in result

    def test_15a_tag_search_with_empty_query(self, app):
        for q in ("missing", None, "", "  "):
            paramd = {}
            if q != "missing":
                paramd["q"] = q
            res = app.post("/api/action/tag_search", json=paramd)
            assert res.json["success"] is True
            assert res.json["result"]["count"] == 0
            assert res.json["result"]["results"] == []

    def test_15a_tag_search_with_no_matches(self, app):
        paramd = {"q": "no matches"}
        res = app.post("/api/action/tag_search", json=paramd)
        assert res.json["success"] is True
        assert res.json["result"]["count"] == 0
        assert res.json["result"]["results"] == []

    def test_15a_tag_search_with_one_match(self, app):
        paramd = {"q": "russ"}
        res = app.post("/api/action/tag_search", json=paramd)
        assert res.json["success"] is True
        assert res.json["result"]["count"] == 1
        tag_dicts = res.json["result"]["results"]
        assert len(tag_dicts) == 1
        assert tag_dicts[0]["name"] == "russian"

    def test_15a_tag_search_with_one_match_using_fields_parameter(self, app):
        paramd = {"fields": {"tags": "russ"}}
        res = app.post("/api/action/tag_search", json=paramd)
        assert res.json["success"] is True
        assert res.json["result"]["count"] == 1
        tag_dicts = res.json["result"]["results"]
        assert len(tag_dicts) == 1
        assert tag_dicts[0]["name"] == "russian"

    def test_15a_tag_search_with_many_matches(self, app):
        paramd = {"q": "tol"}
        res = app.post("/api/action/tag_search", json=paramd)
        assert res.json["success"] is True
        assert res.json["result"]["count"] == 5
        tag_dicts = res.json["result"]["results"]
        assert [tag["name"] for tag in tag_dicts] == sorted(
            ["tolkien", "toledo", "tolerance", "tollbooth", "tolstoy"]
        )

    def test_15a_tag_search_with_many_matches_paged(self, app):
        paramd = {"q": "tol", "limit": 2, "offset": 2}
        res = app.post("/api/action/tag_search", json=paramd)
        assert res.json["success"] is True
        assert res.json["result"]["count"] == 5
        tag_dicts = res.json["result"]["results"]
        assert [tag["name"] for tag in tag_dicts] == [u"tolkien", u"tollbooth"]

    def test_15a_tag_search_with_vocab_and_empty_query(self, app):
        for q in ("missing", None, "", "  "):
            paramd = {"vocabulary_id": "genre"}
            if q != "missing":
                paramd["q"] = q
            res = app.post("/api/action/tag_search", json=paramd)
            assert res.json["success"] is True
            assert res.json["result"]["count"] == 0
            assert res.json["result"]["results"] == []

    def test_15a_tag_search_with_vocab_and_one_match(self, app):
        paramd = {"q": "son", "vocabulary_id": "genre"}
        res = app.post("/api/action/tag_search", json=paramd)
        assert res.json["success"] is True
        assert res.json["result"]["count"] == 1
        tag_dicts = res.json["result"]["results"]
        assert len(tag_dicts) == 1
        assert tag_dicts[0]["name"] == "sonata"

    def test_15a_tag_search_with_vocab_and_multiple_matches(self, app):
        paramd = {"q": "neo", "vocabulary_id": "genre"}
        res = app.post("/api/action/tag_search", json=paramd)
        assert res.json["success"] is True
        assert res.json["result"]["count"] == 6
        tag_dicts = res.json["result"]["results"]
        assert [tag["name"] for tag in tag_dicts] == sorted(
            (
                "neoclassical",
                "neofolk",
                "neomedieval",
                "neoprog",
                "neopsychedelia",
                "neosoul",
            )
        )

    def test_15a_tag_search_with_vocab_and_no_matches(self, app):
        paramd = {"q": "xxxxxxx", "vocabulary_id": "genre"}
        res = app.post("/api/action/tag_search", json=paramd)
        assert res.json["success"] is True
        assert res.json["result"]["count"] == 0
        tag_dicts = res.json["result"]["results"]
        assert tag_dicts == []

    def test_15a_tag_search_with_vocab_that_does_not_exist(self, app):
        paramd = {"q": "neo", "vocabulary_id": "xxxxxx"}
        app.post("/api/action/tag_search", json=paramd, status=404)

    def test_15a_tag_search_with_invalid_vocab(self, app):
        for vocab_name in (None, "", "a", "e" * 200):
            paramd = {"q": "neo", "vocabulary_id": vocab_name}
            app.post("/api/action/tag_search", json=paramd, status=404)

    def test_15_tag_autocomplete(self, app):
        # Empty query
        res = app.post("/api/action/tag_autocomplete", json={})
        res_obj = json.loads(res.body)
        assert res_obj["success"] == True
        assert res_obj["result"] == []
        assert (
            "/api/3/action/help_show?name=tag_autocomplete" in res_obj["help"]
        )

        # Normal query
        res = app.post("/api/action/tag_autocomplete", json={"q": "r"})
        res_obj = json.loads(res.body)
        assert res_obj["success"] == True
        assert res_obj["result"] == ["russian", "tolerance"]
        assert (
            "/api/3/action/help_show?name=tag_autocomplete" in res_obj["help"]
        )

    def test_15_tag_autocomplete_tag_with_spaces(self, app):
        """Asserts autocomplete finds tags that contain spaces"""

        CreateTestData.create_arbitrary(
            [
                {
                    "name": u"package-with-tag-that-has-a-space-1",
                    "tags": [u"with space"],
                    "license": "never_heard_of_it",
                }
            ]
        )

        res = app.post("/api/action/tag_autocomplete", json={"q": "w"})
        res_obj = json.loads(res.body)
        assert res_obj["success"]
        assert "with space" in res_obj["result"], res_obj["result"]

    def test_15_tag_autocomplete_tag_with_foreign_characters(self, app):
        """Asserts autocomplete finds tags that contain foreign characters"""

        CreateTestData.create_arbitrary(
            [
                {
                    "name": u"package-with-tag-that-has-a-foreign-character-1",
                    "tags": [u"greek beta \u03b2"],
                    "license": "never_heard_of_it",
                }
            ]
        )

        res = app.post("/api/action/tag_autocomplete", json={"q": "greek"})
        res_obj = json.loads(res.body)
        assert res_obj["success"]
        assert u"greek beta \u03b2" in res_obj["result"], res_obj["result"]

    def test_15_tag_autocomplete_tag_with_punctuation(self, app):
        """Asserts autocomplete finds tags that contain punctuation"""

        CreateTestData.create_arbitrary(
            [
                {
                    "name": u"package-with-tag-that-has-a-fullstop-1",
                    "tags": [u"fullstop."],
                    "license": "never_heard_of_it",
                }
            ]
        )

        res = app.post("/api/action/tag_autocomplete", json={"q": "fullstop"})
        res_obj = json.loads(res.body)
        assert res_obj["success"]
        assert u"fullstop." in res_obj["result"], res_obj["result"]

    def test_15_tag_autocomplete_tag_with_capital_letters(self, app):
        """
        Asserts autocomplete finds tags that contain capital letters
        """

        CreateTestData.create_arbitrary(
            [
                {
                    "name": u"package-with-tag-that-has-a-capital-letter-1",
                    "tags": [u"CAPITAL idea old chap"],
                    "license": "never_heard_of_it",
                }
            ]
        )

        res = app.post("/api/action/tag_autocomplete", json={"q": "idea"})
        res_obj = json.loads(res.body)
        assert res_obj["success"]
        assert u"CAPITAL idea old chap" in res_obj["result"], res_obj["result"]

    def test_15_tag_autocomplete_search_with_space(self, app):
        """
        Asserts that a search term containing a space works correctly
        """

        CreateTestData.create_arbitrary(
            [
                {
                    "name": u"package-with-tag-that-has-a-space-2",
                    "tags": [u"with space"],
                    "license": "never_heard_of_it",
                }
            ]
        )

        res = app.post("/api/action/tag_autocomplete", json={"q": "th sp"})
        res_obj = json.loads(res.body)
        assert res_obj["success"]
        assert "with space" in res_obj["result"], res_obj["result"]

    def test_15_tag_autocomplete_search_with_foreign_character(self, app):
        """
        Asserts that a search term containing a foreign character works correctly
        """

        CreateTestData.create_arbitrary(
            [
                {
                    "name": u"package-with-tag-that-has-a-foreign-character-2",
                    "tags": [u"greek beta \u03b2"],
                    "license": "never_heard_of_it",
                }
            ]
        )

        res = app.post("/api/action/tag_autocomplete", json={"q": u"\u03b2"})
        res_obj = json.loads(res.body)
        assert res_obj["success"]
        assert u"greek beta \u03b2" in res_obj["result"], res_obj["result"]

    def test_15_tag_autocomplete_search_with_punctuation(self, app):
        """
        Asserts that a search term containing punctuation works correctly
        """

        CreateTestData.create_arbitrary(
            [
                {
                    "name": u"package-with-tag-that-has-a-fullstop-2",
                    "tags": [u"fullstop."],
                    "license": "never_heard_of_it",
                }
            ]
        )

        res = app.post("/api/action/tag_autocomplete", json={"q": u"stop."})
        res_obj = json.loads(res.body)
        assert res_obj["success"]
        assert "fullstop." in res_obj["result"], res_obj["result"]

    def test_15_tag_autocomplete_search_with_capital_letters(self, app):
        """
        Asserts that a search term containing capital letters works correctly
        """

        CreateTestData.create_arbitrary(
            [
                {
                    "name": u"package-with-tag-that-has-a-capital-letter-2",
                    "tags": [u"CAPITAL idea old chap"],
                    "license": "never_heard_of_it",
                }
            ]
        )

        res = app.post("/api/action/tag_autocomplete", json={"q": u"CAPITAL"})
        res_obj = json.loads(res.body)
        assert res_obj["success"]
        assert "CAPITAL idea old chap" in res_obj["result"], res_obj["result"]

    def test_15_tag_autocomplete_is_case_insensitive(self, app):
        CreateTestData.create_arbitrary(
            [
                {
                    "name": u"package-with-tag-that-has-a-capital-letter-3",
                    "tags": [u"MIX of CAPITALS and LOWER case"],
                    "license": "never_heard_of_it",
                }
            ]
        )

        res = app.post("/api/action/tag_autocomplete", json={"q": u"lower case"})
        res_obj = json.loads(res.body)
        assert res_obj["success"]
        assert "MIX of CAPITALS and LOWER case" in res_obj["result"], res_obj[
            "result"
        ]

    def test_15_tag_autocomplete_with_vocab_and_empty_query(self, app):
        for q in ("missing", None, "", "  "):
            paramd = {"vocabulary_id": u"genre"}
            if q != "missing":
                paramd["q"] = q
            res = app.post("/api/action/tag_autocomplete", json=paramd)
            assert res.json["success"] is True
            assert res.json["result"] == []

    def test_15_tag_autocomplete_with_vocab_and_single_match(self, app):
        paramd = {"vocabulary_id": u"genre", "q": "son"}
        res = app.post("/api/action/tag_autocomplete", json=paramd)
        assert res.json["success"] is True
        assert res.json["result"] == ["sonata"], res.json["result"]

    def test_15_tag_autocomplete_with_vocab_and_multiple_matches(self, app):
        paramd = {"vocabulary_id": "genre", "q": "neo"}
        res = app.post("/api/action/tag_autocomplete", json=paramd)
        assert res.json["success"] is True
        assert res.json["result"] == sorted(
            (
                "neoclassical",
                "neofolk",
                "neomedieval",
                "neoprog",
                "neopsychedelia",
                "neosoul",
            )
        )

    def test_15_tag_autocomplete_with_vocab_and_no_matches(self, app):
        paramd = {"vocabulary_id": "composers", "q": "Jonny Greenwood"}
        res = app.post("/api/action/tag_autocomplete", json=paramd)
        assert res.json["success"] is True
        assert res.json["result"] == []

    def test_15_tag_autocomplete_with_vocab_that_does_not_exist(self, app):
        for q in ("", "neo"):
            paramd = {"vocabulary_id": "does_not_exist", "q": q}

            res = app.post(
                "/api/action/tag_autocomplete", json=paramd, status=404
            )
            assert res.json["success"] is False

    def test_15_tag_autocomplete_with_invalid_vocab(self, app):
        for vocab_name in (None, "", "a", "e" * 200):
            for q in (None, "", "son"):
                paramd = {"vocabulary_id": vocab_name, "q": q}
                res = app.post(
                    "/api/action/tag_autocomplete", json=paramd, status=404
                )
                assert res.json["success"] is False
