"""Tests for actions and authorization in ckan/logic/action/term_translation.py."""

import pytest

import ckan.tests.helpers as helpers


@pytest.mark.usefixtures("non_clean_db")
def test_update_single(app):

    data = {"term": "moo", "term_translation": "moo", "lang_code": "fr"}
    helpers.call_action("term_translation_update", **data)
    data = {
        "term": "moo",
        "term_translation": "moomoo",
        "lang_code": "fr",
    }
    helpers.call_action("term_translation_update", **data)
    data = {
        "term": "moo",
        "term_translation": "moomoo",
        "lang_code": "en",
    }
    helpers.call_action("term_translation_update", **data)
    result = helpers.call_action("term_translation_show", terms=["moo"])

    assert sorted(result, key=dict.items) == sorted(
        [
            {
                "lang_code": "fr",
                "term": "moo",
                "term_translation": "moomoo",
            },
            {
                "lang_code": "en",
                "term": "moo",
                "term_translation": "moomoo",
            },
        ],
        key=dict.items,
    )


@pytest.mark.usefixtures("non_clean_db")
def test_2_update_many(app):

    data = [
        {
            "term": "many",
            "term_translation": "manymoo",
            "lang_code": "fr",
        },
        {
            "term": "many",
            "term_translation": "manymoo",
            "lang_code": "en",
        },
        {
            "term": "many",
            "term_translation": "manymoomoo",
            "lang_code": "en",
        },
    ]
    result = helpers.call_action("term_translation_update_many", data=data)
    assert result["success"] == "3 rows updated"

    result = helpers.call_action("term_translation_show", terms=["many"])
    assert sorted(result, key=dict.items) == sorted(
        [
            {
                "lang_code": "fr",
                "term": "many",
                "term_translation": "manymoo",
            },
            {
                "lang_code": "en",
                "term": "many",
                "term_translation": "manymoomoo",
            },
        ],
        key=dict.items,
    )
