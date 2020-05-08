# encoding: utf-8

import pytest
import ckan.lib.create_test_data as ctd
import ckan.lib.navl.dictization_functions as df
import ckan.logic as logic
import ckan.logic.converters as converters
import ckan.model as model
import ckan.tests.legacy as tests

TEST_VOCAB_NAME = "test-vocab"


class TestConverters(object):
    @pytest.fixture(autouse=True)
    def initial_data(self, clean_db):
        self.vocab = model.Vocabulary(TEST_VOCAB_NAME)
        model.Session.add(self.vocab)
        model.Session.commit()
        vocab_tag_1 = model.Tag("tag1", self.vocab.id)
        vocab_tag_2 = model.Tag("tag2", self.vocab.id)
        model.Session.add(vocab_tag_1)
        model.Session.add(vocab_tag_2)
        model.Session.commit()
        model.Session.remove()

    def test_convert_to_tags(self):
        def convert(tag_string, vocab):
            key = "vocab_tags"
            data = {key: tag_string}
            errors = []
            context = {"model": model, "session": model.Session}
            converters.convert_to_tags(vocab)(key, data, errors, context)
            del data[key]
            return data

        data = df.unflatten(convert(["tag1", "tag2"], "test-vocab"))
        for tag in data["tags"]:
            assert tag["name"] in ["tag1", "tag2"], tag["name"]
            assert tag["vocabulary_id"] == self.vocab.id, tag["vocabulary_id"]

    def test_convert_from_tags(self):
        key = "tags"
        data = {
            ("tags", 0, "__extras"): {
                "name": "tag1",
                "vocabulary_id": self.vocab.id,
            },
            ("tags", 1, "__extras"): {
                "name": "tag2",
                "vocabulary_id": self.vocab.id,
            },
        }
        errors = []
        context = {"model": model, "session": model.Session}
        converters.convert_from_tags(self.vocab.name)(
            key, data, errors, context
        )
        assert "tag1" in data["tags"]
        assert "tag2" in data["tags"]

    def test_free_tags_only(self):
        key = ("tags", 0, "__extras")
        data = {
            ("tags", 0, "__extras"): {
                "name": "tag1",
                "vocabulary_id": self.vocab.id,
            },
            ("tags", 0, "vocabulary_id"): self.vocab.id,
            ("tags", 1, "__extras"): {"name": "tag2", "vocabulary_id": None},
            ("tags", 1, "vocabulary_id"): None,
        }
        errors = []
        context = {"model": model, "session": model.Session}
        converters.free_tags_only(key, data, errors, context)
        assert len(data) == 2
        assert ("tags", 1, "vocabulary_id") in data.keys()
        assert ("tags", 1, "__extras") in data.keys()


class TestVocabFacets(object):
    @pytest.fixture(autouse=True)
    def initial_data(self, clean_db, clean_index):
        if not tests.is_search_supported():
            pytest.skip("Search not supported")

        ctd.CreateTestData.create()

        self.vocab = model.Vocabulary(TEST_VOCAB_NAME)
        model.Session.add(self.vocab)
        model.Session.commit()

        vocab_tag_1 = model.Tag("tag1", self.vocab.id)
        vocab_tag_2 = model.Tag("tag2", self.vocab.id)
        model.Session.add(vocab_tag_1)
        model.Session.add(vocab_tag_2)

        pkg = model.Package.get("warandpeace")
        pkg_tag1 = model.PackageTag(pkg, vocab_tag_1)
        pkg_tag2 = model.PackageTag(pkg, vocab_tag_2)
        model.Session.add(pkg_tag1)
        model.Session.add(pkg_tag2)

        model.Session.commit()
        model.Session.remove()

    def test_vocab_facets(self):
        vocab_facet = "vocab_%s" % TEST_VOCAB_NAME

        context = {"model": model, "session": model.Session}
        data = {
            "q": "warandpeace",
            "facet": "true",
            "facet.field": ["groups", "tags", vocab_facet],
            "facet.limit": "50",
            "facet.mincount": 1,
        }

        result = logic.get_action("package_search")(context, data)
        facets = result["search_facets"]
        facet_tags = [t["name"] for t in facets["tags"]["items"]]
        assert len(facet_tags)

        # make sure vocab tags are not in 'tags' facet
        assert "tag1" not in facet_tags
        assert "tag2" not in facet_tags

        # make sure vocab tags are in vocab_<TEST_VOCAB_NAME> facet
        vocab_facet_tags = [t["name"] for t in facets[vocab_facet]["items"]]
        assert "tag1" in vocab_facet_tags
        assert "tag2" in vocab_facet_tags

    def test_vocab_facets_searchable(self):
        context = {"model": model, "session": model.Session}
        data = {"q": "tag1", "facet": "false"}
        result = logic.get_action("package_search")(context, data)
        assert result["count"] == 1
        assert result["results"][0]["name"] == "warandpeace"
