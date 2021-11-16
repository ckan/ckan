# encoding: utf-8

import pytest

import ckan.plugins
import ckanext.multilingual.plugin as mulilingual_plugin
import ckan.lib.helpers as h
import ckan.lib.create_test_data
import ckan.model as model
from ckan.tests.helpers import body_contains, call_action

_create_test_data = ckan.lib.create_test_data
ORG_NAME = "test_org"


@pytest.fixture
def prepare(clean_db, clean_index, with_request_context):
    _create_test_data.CreateTestData.create_translations_test_data()

    sysadmin_user = model.User.get("testsysadmin")
    org = {
        "name": ORG_NAME,
        "title": "russian",
        "description": "Roger likes these books.",
    }
    context = {"user": sysadmin_user.name}
    call_action("organization_create", context, **org)
    dataset = {
        "name": "test_org_dataset",
        "title": "A Novel By Tolstoy",
        "owner_org": org["name"],
    }
    context = {"user": sysadmin_user.name}
    call_action("package_create", context, **dataset)

    # Add translation terms that match a couple of group names and package
    # names. Group names and package names should _not_ get translated even
    # if there are terms matching them, because they are used to form URLs.
    for term in ("roger", "david", "annakarenina", "warandpeace"):
        for lang_code in ("en", "de", "fr"):
            data_dict = {
                "term": term,
                "term_translation": "this should not be rendered",
                "lang_code": lang_code,
            }
            call_action("term_translation_update", **data_dict)


@pytest.mark.usefixtures("prepare", "with_plugins")
@pytest.mark.ckan_config(
    "ckan.plugins", "multilingual_dataset multilingual_group multilingual_tag"
)
class TestDatasetTermTranslation:
    "Test the translation of datasets by the multilingual_dataset plugin."

    def test_user_read_translation(self, app):
        """Test the translation of datasets on user view pages by the
        multilingual_dataset plugin.

        """

        # It is testsysadmin who created the dataset, so testsysadmin whom
        # we'd expect to see the datasets for.
        for user_name in ("testsysadmin",):
            offset = str(h.url_for("user.read", id=user_name))
            for (lang_code, translations) in (
                ("de", _create_test_data.german_translations),
                ("fr", _create_test_data.french_translations),
                ("en", _create_test_data.english_translations),
                ("pl", {}),
            ):
                response = app.get(
                    offset,
                    status=200,
                    extra_environ={
                        "CKAN_LANG": lang_code,
                        "CKAN_CURRENT_URL": offset,
                    },
                )
                terms = "A Novel By Tolstoy"
                for term in terms:
                    if term in translations:
                        assert body_contains(response, translations[term])
                    elif term in _create_test_data.english_translations:
                        assert body_contains(
                            response,
                            _create_test_data.english_translations[term],
                        )
                    else:
                        assert body_contains(response, term)
                assert not body_contains(
                    response, "this should not be rendered"
                )

    def test_org_read_translation(self, app):
        for (lang_code, translations) in (
            ("de", _create_test_data.german_translations),
            ("fr", _create_test_data.french_translations),
            ("en", _create_test_data.english_translations),
            ("pl", {}),
        ):
            offset = "/{0}/organization/{1}".format(lang_code, ORG_NAME)
            response = app.get(offset, status=200)
            terms = (
                "A Novel By Tolstoy",
                "russian",
                "Roger likes these books.",
            )
            for term in terms:
                if term in translations:
                    assert body_contains(response, translations[term])
                elif term in _create_test_data.english_translations:
                    assert body_contains(
                        response, _create_test_data.english_translations[term]
                    )
                else:
                    assert body_contains(response, term)
            assert not body_contains(response, "this should not be rendered")

    def test_org_index_translation(self, app):
        for (lang_code, translations) in (
            ("de", _create_test_data.german_translations),
            ("fr", _create_test_data.french_translations),
            ("en", _create_test_data.english_translations),
            ("pl", {}),
        ):
            offset = "/{0}/organization".format(lang_code)
            response = app.get(offset, status=200)
            for term in ("russian", "Roger likes these books."):
                if term in translations:
                    assert body_contains(response, translations[term])
                elif term in _create_test_data.english_translations:
                    assert body_contains(
                        response, _create_test_data.english_translations[term]
                    )
                else:
                    assert body_contains(response, term)
            assert body_contains(
                response, "/{0}/organization/{1}".format(lang_code, ORG_NAME)
            )
            assert not body_contains(response, "this should not be rendered")


@pytest.mark.ckan_config(
    "ckan.plugins", "multilingual_dataset multilingual_group multilingual_tag"
)
@pytest.mark.usefixtures("clean_db", "clean_index", "with_plugins")
class TestDatasetSearchIndex(object):
    def test_translate_terms(self):
        data_dicts = [
            {
                "term": "moo",
                "term_translation": "french_moo",
                "lang_code": "fr",
            },
            {
                "term": "moo",
                "term_translation": "this should not be rendered",
                "lang_code": "fsdas",
            },
            {
                "term": "an interesting note",
                "term_translation": "french note",
                "lang_code": "fr",
            },
            {
                "term": "moon",
                "term_translation": "french moon",
                "lang_code": "fr",
            },
            {
                "term": "boon",
                "term_translation": "french boon",
                "lang_code": "fr",
            },
            {
                "term": "boon",
                "term_translation": "italian boon",
                "lang_code": "it",
            },
            {
                "term": "david",
                "term_translation": "french david",
                "lang_code": "fr",
            },
            {
                "term": "david",
                "term_translation": "italian david",
                "lang_code": "it",
            },
        ]

        for data_dict in data_dicts:
            call_action("term_translation_update", **data_dict)

        sample_index_data = {
            "download_url": u"moo",
            "notes": u"an interesting note",
            "tags": [u"moon", "boon"],
            "title": u"david",
        }

        result = mulilingual_plugin.MultilingualDataset().before_dataset_index(
            sample_index_data
        )
        assert result == {
            "text_sr@latin": "",
            "text_fi": "",
            "text_de": "",
            "text_pt_BR": "",
            u"title_fr": u"french david",
            "text_fr": u"french_moo french note french moon french boon",
            "text_ja": "",
            "text_sr": "",
            "title": u"david",
            "text_ca": "",
            "download_url": u"moo",
            "text_hu": "",
            "text_sa": "",
            "text_cs_CZ": "",
            "text_nl": "",
            "text_no": "",
            "text_ko_KR": "",
            "text_sk": "",
            "text_bg": "",
            "text_sv": "",
            "tags": [u"moon", "boon"],
            "text_el": "",
            "title_en": u"david",
            "text_en": u"moo an interesting note moon boon",
            "text_es": "",
            "text_sl": "",
            "text_pl": "",
            "notes": u"an interesting note",
            "text_lv": "",
            "text_it": u"italian boon",
            u"title_it": u"italian david",
            "text_ru": "",
        }, result
