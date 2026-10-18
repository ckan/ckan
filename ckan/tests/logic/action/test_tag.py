"""Tests for actions and authorization in ckan/logic/action/tag.py."""

import operator

import pytest

import ckan.logic as logic
import ckan.model as model
import ckan.tests.factories as factories
import ckan.tests.helpers as helpers
from ckan.lib.navl.dictization_functions import DataError


@pytest.mark.usefixtures("non_clean_db")
def test_basic():
    name = factories.Vocabulary.stub().name
    vocab = helpers.call_action("vocabulary_create", name=name)
    obj = model.Vocabulary.get(name)
    assert obj.id == vocab["id"]


@pytest.mark.usefixtures("non_clean_db")
def test_with_tags():
    name = factories.Vocabulary.stub().name
    tag1 = factories.Tag.stub().name
    tag2 = factories.Tag.stub().name
    tags = [{"name": tag1}, {"name": tag2}]
    helpers.call_action("vocabulary_create", name=name, tags=tags)
    vocab = helpers.call_action("vocabulary_show", id=name)
    assert vocab["name"] == name
    assert len(vocab["tags"]) == 2
    for tag in vocab["tags"]:
        assert tag["vocabulary_id"] == vocab["id"]
        assert tag["name"] in {tag1, tag2}


@pytest.mark.usefixtures("non_clean_db")
def test_with_empty_tags():
    name = factories.Vocabulary.stub().name
    resp = helpers.call_action("vocabulary_create", name=name, tags=[])
    assert resp["tags"] == []


@pytest.mark.usefixtures("non_clean_db")
def test_with_existing_name():
    name = factories.Vocabulary.stub().name
    helpers.call_action("vocabulary_create", name=name, tags=[])
    with pytest.raises(logic.ValidationError):
        helpers.call_action("vocabulary_create", name=name, tags=[])


@pytest.mark.parametrize(
    "tags",
    [
        [{"id": "xxx"}, {"name": "foo"}],
        [{"name": "foo"}, {"name": None}],
        [{"name": "foo"}, {"name": ""}],
        [{"name": "foo"}, {"name": "f"}],
        [{"name": "f" * 200}, {"name": "foo"}],
        [{"name": "Invalid!"}, {"name": "foo"}],
    ],
)
def test_with_bad_tags(tags):
    name = factories.Vocabulary.stub().name
    with pytest.raises(logic.ValidationError):
        helpers.call_action("vocabulary_create", name=name, tags=tags)


def test_with_no_tags():
    name = factories.Vocabulary.stub().name
    with pytest.raises(DataError):
        helpers.call_action("vocabulary_create", name=name, tags=None)


def test_id_not_allowed():
    name = factories.Vocabulary.stub().name
    with pytest.raises(logic.ValidationError):
        helpers.call_action("vocabulary_create", name=name, id="xxx")


def test_no_name():
    with pytest.raises(logic.ValidationError):
        helpers.call_action("vocabulary_create")


@pytest.mark.parametrize("name", (None, "", "a", "foobar" * 100))
def test_invalid_name(name):
    with pytest.raises(logic.ValidationError):
        helpers.call_action("vocabulary_create", name=name)


@pytest.mark.usefixtures("non_clean_db")
def test_add_tag_to_vocab():
    tag1 = factories.Tag.stub().name
    tag2 = factories.Tag.stub().name
    vocab = factories.Vocabulary(tags=[{"name": tag1}])
    assert set(map(operator.itemgetter("name"), vocab["tags"])) == {tag1}
    helpers.call_action("tag_create", name=tag2, vocabulary_id=vocab["id"])

    vocab = helpers.call_action("vocabulary_show", id=vocab["id"])
    assert set(map(operator.itemgetter("name"), vocab["tags"])) == {
        tag1,
        tag2,
    }


def test_no_vocab():
    with pytest.raises(logic.ValidationError):
        helpers.call_action("tag_create", name=factories.Tag.stub().name)


def test_does_not_exist():
    with pytest.raises(logic.ValidationError):
        helpers.call_action(
            "tag_create",
            name=factories.Tag.stub().name,
            vocabulary_id=factories.Vocabulary.stub().name,
        )


@pytest.mark.usefixtures("non_clean_db")
def test_duplicate():
    tag1 = factories.Tag.stub().name
    vocab = factories.Vocabulary(tags=[{"name": tag1}])
    with pytest.raises(logic.ValidationError):
        helpers.call_action("tag_create", name=tag1, vocabulary_id=vocab["id"])


@pytest.mark.usefixtures("non_clean_db")
def test_tagcreate_id_not_allowed():
    vocab = factories.Vocabulary()
    with pytest.raises(logic.ValidationError):
        helpers.call_action(
            "tag_create", name="foo", id="xxx", vocabulary_id=vocab["id"]
        )


@pytest.mark.usefixtures("non_clean_db")
def test_name_is_required():
    vocab = factories.Vocabulary()
    with pytest.raises(logic.ValidationError):
        helpers.call_action("tag_create", vocabulary_id=vocab["id"])


@pytest.mark.usefixtures("non_clean_db")
def test_tagcreate_invalid_name():
    vocab = factories.Vocabulary()
    for name in ("Not a valid tag name!", "", None):
        with pytest.raises(logic.ValidationError):
            helpers.call_action("tag_create", name=name, vocabulary_id=vocab["id"])


def test_tag_delete_with_unicode_returns_unicode_error():
    # There is not a lot of call for it, but in theory there could be
    # unicode in the ActionError error message, so ensure that comes
    # through in NotFound as unicode.
    with pytest.raises(logic.NotFound) as e:
        helpers.call_action("tag_delete", id="Delta symbol: \u0394")
    assert "Delta symbol: \u0394" in e.value.message


def test_no_id():
    with pytest.raises(logic.ValidationError):
        helpers.call_action("tag_delete")


def test_deletetags_does_not_exist():
    with pytest.raises(logic.NotFound):
        helpers.call_action("tag_delete", id="not-a-real-id")


@pytest.mark.usefixtures("non_clean_db")
def test_vocab_does_not_exist():
    vocab = factories.Vocabulary(tags=[{"name": "testtag"}])
    tag = vocab["tags"][0]
    with pytest.raises(logic.NotFound):
        helpers.call_action("tag_delete", id=tag["id"], vocabulary_id="not-a-real-id")


@pytest.mark.usefixtures("clean_db")
def test_delete_tag():
    tag1 = factories.Tag.stub().name
    tag2 = factories.Tag.stub().name
    pkg = factories.Dataset(tags=[{"name": tag2}, {"name": tag1}])
    assert len(pkg["tags"]) == 2
    tags = {t["name"] for t in pkg["tags"]}
    assert set(helpers.call_action("tag_list")) == tags

    for tag in pkg["tags"]:
        helpers.call_action("tag_delete", id=tag["id"])

    assert helpers.call_action("tag_list") == []
    pkg = helpers.call_action("package_show", id=pkg["id"])
    assert pkg["tags"] == []


@pytest.mark.usefixtures("non_clean_db")
def test_vocabularydelete_basic():
    vocab = factories.Vocabulary()
    helpers.call_action("vocabulary_delete", id=vocab["id"])

    assert vocab["id"] not in {
        v["name"] for v in helpers.call_action("vocabulary_list")
    }


@pytest.mark.usefixtures("non_clean_db")
def test_not_existing():
    with pytest.raises(logic.NotFound):
        helpers.call_action("vocabulary_delete", id="does-not-exist")


def test_vocabularydelete_no_id():
    with pytest.raises(logic.ValidationError):
        helpers.call_action("vocabulary_delete")


@pytest.mark.usefixtures("non_clean_db")
def test_tag_show_for_free_tag():
    tag = factories.Tag.stub().name
    dataset = factories.Dataset(tags=[{"name": tag}])
    tag_in_dataset = dataset["tags"][0]

    tag_shown = helpers.call_action("tag_show", id=tag)

    assert tag_shown["name"] == tag
    assert tag_shown["display_name"] == tag
    assert tag_shown["id"] == tag_in_dataset["id"]
    assert tag_shown["vocabulary_id"] is None
    assert "packages" not in tag_shown


@pytest.mark.usefixtures("non_clean_db")
@pytest.mark.usefixtures("clean_index")
def test_tag_show_with_datasets():
    tag = factories.Tag.stub().name
    dataset = factories.Dataset(tags=[{"name": tag}])

    tag_shown = helpers.call_action("tag_show", id=tag, include_datasets=True)

    assert [d["name"] for d in tag_shown["packages"]] == [dataset["name"]]


@pytest.mark.usefixtures("non_clean_db")
def test_tag_show_not_found():
    with pytest.raises(logic.NotFound):
        helpers.call_action("tag_show", id=factories.Tag.stub().name)


@pytest.mark.usefixtures("non_clean_db")
@pytest.mark.usefixtures("clean_db")
def test_tag_show_for_flexible_tag():
    # A 'flexible' tag is one with spaces, some punctuation
    # and foreign characters in its name
    dataset = factories.Dataset(tags=[{"name": "Flexible. \u30a1"}])

    tag_shown = helpers.call_action(
        "tag_show", id="Flexible. \u30a1", include_datasets=True
    )

    assert tag_shown["name"] == "Flexible. \u30a1"
    assert tag_shown["display_name"] == "Flexible. \u30a1"
    assert [d["name"] for d in tag_shown["packages"]] == [dataset["name"]]


@pytest.mark.usefixtures("non_clean_db")
def test_tag_show_for_vocab_tag():
    tag = factories.Tag.stub().name
    vocab = factories.Vocabulary(tags=[dict(name=tag)])
    dataset = factories.Dataset(tags=vocab["tags"])
    tag_in_dataset = dataset["tags"][0]

    tag_shown = helpers.call_action(
        "tag_show",
        id=tag,
        vocabulary_id=vocab["id"],
        include_datasets=True,
    )

    assert tag_shown["name"] == tag
    assert tag_shown["display_name"] == tag
    assert tag_shown["id"] == tag_in_dataset["id"]
    assert tag_shown["vocabulary_id"] == vocab["id"]
    assert [d["name"] for d in tag_shown["packages"]] == [dataset["name"]]


@pytest.mark.usefixtures("clean_db")
def test_tag_list():
    tag = factories.Tag.stub().name
    tag2 = factories.Tag.stub().name
    factories.Dataset(tags=[{"name": tag}, {"name": tag2}])
    factories.Dataset(tags=[{"name": tag2}])

    tag_list = helpers.call_action("tag_list")

    assert set(tag_list) == set((tag, tag2))


@pytest.mark.usefixtures("clean_db")
def test_tag_list_all_fields():
    factories.Dataset(tags=[{"name": "acid-rain"}])

    tag_list = helpers.call_action("tag_list", all_fields=True)

    assert tag_list[0]["name"] == "acid-rain"
    assert tag_list[0]["display_name"] == "acid-rain"
    assert "packages" not in tag_list


@pytest.mark.usefixtures("clean_db")
def test_tag_list_with_flexible_tag():
    # A 'flexible' tag is one with spaces, punctuation (apart from commas)
    # and foreign characters in its name
    flexible_tag = "Flexible. \u30a1"
    factories.Dataset(tags=[{"name": flexible_tag}])

    tag_list = helpers.call_action("tag_list", all_fields=True)

    assert tag_list[0]["name"] == flexible_tag


@pytest.mark.usefixtures("clean_db")
def test_tag_list_with_vocab():
    vocab = factories.Vocabulary(tags=[dict(name="acid-rain"), dict(name="pollution")])

    tag_list = helpers.call_action("tag_list", vocabulary_id=vocab["id"])

    assert set(tag_list) == set(("acid-rain", "pollution"))


@pytest.mark.usefixtures("clean_db")
def test_tag_list_vocab_not_found():
    with pytest.raises(logic.NotFound):
        helpers.call_action("tag_list", vocabulary_id="does-not-exist")


@pytest.mark.usefixtures("non_clean_db")
def test_no_real_update():
    vocab = factories.Vocabulary()
    updated = helpers.call_action("vocabulary_update", id=vocab["id"])
    assert vocab == updated

    updated = helpers.call_action(
        "vocabulary_update", id=vocab["id"], name=vocab["name"]
    )
    assert vocab == updated


@pytest.mark.usefixtures("non_clean_db")
def test_update_name():
    vocab = factories.Vocabulary()
    stub = factories.Vocabulary.stub()

    updated = helpers.call_action("vocabulary_update", id=vocab["id"], name=stub.name)
    assert updated["name"] == stub.name


@pytest.mark.usefixtures("non_clean_db")
def test_add_tags():
    vocab = factories.Vocabulary()
    assert vocab["tags"] == []

    tags = [
        {"name": factories.Tag.stub().name},
        {"name": factories.Tag.stub().name},
    ]

    updated = helpers.call_action("vocabulary_update", id=vocab["id"], tags=tags)
    assert {t["name"] for t in updated["tags"]} == {t["name"] for t in tags}

    tags.append(
        {"name": factories.Tag.stub().name},
    )
    updated = helpers.call_action("vocabulary_update", id=vocab["id"], tags=tags)
    assert {t["name"] for t in updated["tags"]} == {t["name"] for t in tags}


def test_non_existing():
    with pytest.raises(logic.NotFound):
        helpers.call_action("vocabulary_update", id=factories.Vocabulary.stub().name)


def test_missing_id():
    with pytest.raises(logic.ValidationError):
        helpers.call_action("vocabulary_update")


@pytest.mark.parametrize("tags", [])
@pytest.mark.usefixtures("non_clean_db")
def test_vocabularyupdate_with_bad_tags(tags):
    vocab = factories.Vocabulary()
    for tags in [
        [{"id": "xxx"}, {"name": "foo"}],
        [{"name": "foo"}, {"name": None}],
        [{"name": "foo"}, {"name": ""}],
        [{"name": "foo"}, {"name": "f"}],
        [{"name": "f" * 200}, {"name": "foo"}],
        [{"name": "Invalid!"}, {"name": "foo"}],
    ]:
        with pytest.raises(logic.ValidationError):
            helpers.call_action("vocabulary_update", id=vocab["id"], tags=tags)


@pytest.mark.usefixtures("non_clean_db")
def test_vocabularyupdate_with_no_tags():
    vocab = factories.Vocabulary()
    with pytest.raises(DataError):
        helpers.call_action("vocabulary_update", id=vocab["id"], tags=None)


@pytest.mark.usefixtures("non_clean_db")
def test_clen_tags():
    vocab = factories.Vocabulary(tags=[{"name": factories.Tag.stub().name}])
    updated = helpers.call_action("vocabulary_update", id=vocab["id"], tags=[])
    assert updated["tags"] == []
