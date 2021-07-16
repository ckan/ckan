# encoding: utf-8

import pytest
from ckan import model
import ckan.lib.search as search

from ckan.tests.legacy import CreateTestData, setup_test_search_index
from ckan.tests.legacy.lib import check_search_results


class TestQuery:
    def test_1_convert_legacy_params_to_solr(self):
        convert = search.convert_legacy_parameters_to_solr
        assert convert({"title": "bob"}) == {"q": "title:bob"}
        assert convert({"title": "bob", "fl": "name"}) == {
            "q": "title:bob",
            "fl": "name",
        }
        assert convert({"title": "bob perkins"}) == {
            "q": 'title:"bob perkins"'
        }
        assert convert({"q": "high+wages"}) == {"q": "high wages"}
        assert convert({"q": "high+wages summary"}) == {
            "q": "high wages summary"
        }
        assert convert({"title": "high+wages"}) == {"q": 'title:"high wages"'}
        assert convert({"title": "bob", "all_fields": 1}) == {
            "q": "title:bob",
            "fl": "*",
        }
        with pytest.raises(search.SearchError):
            convert({"title": "bob", "all_fields": "non-boolean"})
        assert convert({"q": "bob", "order_by": "name"}) == {
            "q": "bob",
            "sort": "name asc",
        }
        assert convert({"q": "bob", "offset": "0", "limit": "10"}) == {
            "q": "bob",
            "start": "0",
            "rows": "10",
        }
        assert convert({"tags": ["russian", "tolstoy"]}) == {
            "q": 'tags:"russian" tags:"tolstoy"'
        }
        assert convert({"tags": ["russian", "multi word"]}) == {
            "q": 'tags:"russian" tags:"multi word"'
        }
        assert convert({"tags": ["with CAPITALS"]}) == {
            "q": 'tags:"with CAPITALS"'
        }
        assert convert({"tags": ["with greek omega \u03a9"]}) == {
            "q": 'tags:"with greek omega \u03a9"'
        }
        assert convert({"tags": ["tolstoy"]}) == {"q": 'tags:"tolstoy"'}
        assert convert({"tags": "tolstoy"}) == {"q": 'tags:"tolstoy"'}
        assert convert({"tags": "more than one tolstoy"}) == {
            "q": 'tags:"more than one tolstoy"'
        }
        assert convert({"tags": "with greek omega \u03a9"}) == {
            "q": 'tags:"with greek omega \u03a9"'
        }
        assert convert({"title": "Seymour: An Introduction"}) == {
            "q": 'title:"Seymour\: An Introduction"'
        }
        assert convert({"title": "Pop!"}) == {"q": "title:Pop\!"}

        with pytest.raises(search.SearchError):
            convert({"tags": {"tolstoy": 1}})


class TestSearch(object):
    # 'penguin' is in all test search packages
    q_all = "penguin"

    @pytest.fixture(autouse=True)
    def setup_class(self, clean_db, clean_index):
        CreateTestData.create_search_test_data()
        # now remove a tag so we can test search with deleted tags
        gils = model.Package.by_name("gils")
        # an existing tag used only by gils
        self.tagname = "registry"
        idx = [t.name for t in gils.get_tags()].index(self.tagname)
        gils.remove_tag(gils.get_tags()[idx])
        model.repo.commit_and_remove()

    def _pkg_names(self, result):
        return " ".join(result["results"])

    def _check_entity_names(self, result, names_in_result):
        names = result["results"]
        for name in names_in_result:
            if name not in names:
                return False
        return True

    def test_1_all_records(self):
        result = search.query_for(model.Package).run({"q": self.q_all})
        assert "gils" in result["results"], result["results"]
        assert result["count"] == 6, result["count"]

    def test_1_name(self):
        # exact name
        result = search.query_for(model.Package).run({"q": "gils"})
        assert result["count"] == 1, result
        assert self._pkg_names(result) == "gils", result

    def test_1_name_multiple_results(self):
        result = search.query_for(model.Package).run({"q": "gov"})
        assert self._check_entity_names(
            result, ("us-gov-images", "usa-courts-gov")
        ), self._pkg_names(result)
        assert result["count"] == 4, self._pkg_names(result)

    def test_1_name_token(self):
        result = search.query_for(model.Package).run({"q": "name:gils"})
        assert self._pkg_names(result) == "gils", self._pkg_names(result)
        result = search.query_for(model.Package).run({"q": "title:gils"})
        assert not self._check_entity_names(result, ("gils")), self._pkg_names(
            result
        )

    def test_2_title(self):
        # exact title, one word
        result = search.query_for(model.Package).run({"q": "Opengov"})

        assert self._pkg_names(result) == "se-opengov", self._pkg_names(result)
        # multiple words
        result = search.query_for(model.Package).run(
            {"q": "Government Expenditure"}
        )
        # uk-government-expenditure is the best match but all other results should be retured
        assert self._pkg_names(result).startswith(
            "uk-government-expenditure"
        ), self._pkg_names(result)
        # multiple words wrong order
        result = search.query_for(model.Package).run(
            {"q": "Expenditure Government"}
        )
        assert self._pkg_names(result).startswith(
            "uk-government-expenditure"
        ), self._pkg_names(result)
        # multiple words all should match government

        result = search.query_for(model.Package).run(
            {"q": "Expenditure Government China"}
        )
        assert len(result["results"]) == 1, self._pkg_names(result)

    def test_3_license(self):
        # this should result, but it is here to check that at least it does not error
        result = search.query_for(model.Package).run(
            {"q": 'license:"OKD::Other (PublicsDomain)"'}
        )
        assert result["count"] == 0, result

    def test_quotation(self):
        # multiple words quoted
        result = search.query_for(model.Package).run(
            {"q": '"Government Expenditure"'}
        )
        assert (
            self._pkg_names(result) == "uk-government-expenditure"
        ), self._pkg_names(result)
        # multiple words quoted wrong order
        result = search.query_for(model.Package).run(
            {"q": '"Expenditure Government"'}
        )
        assert self._pkg_names(result) == "", self._pkg_names(result)

    def test_string_not_found(self):
        result = search.query_for(model.Package).run({"q": "randomthing"})
        assert self._pkg_names(result) == "", self._pkg_names(result)

    def test_tags_field(self):
        result = search.query_for(model.Package).run({"q": "country-sweden"})
        assert self._check_entity_names(
            result, ["se-publications", "se-opengov"]
        ), self._pkg_names(result)

    def test_tags_field_split_word(self):
        result = search.query_for(model.Package).run({"q": "todo split"})
        assert self._check_entity_names(
            result, ["us-gov-images"]
        ), self._pkg_names(result)

    def test_tags_field_with_capitals(self):
        result = search.query_for(model.Package).run({"q": "CAPITALS"})
        assert self._check_entity_names(
            result, ["se-publications"]
        ), self._pkg_names(result)

    def dont_test_tags_field_with_basic_unicode(self):
        result = search.query_for(model.Package).run(
            {"q": "greek omega \u03a9"}
        )
        assert self._check_entity_names(
            result, ["se-publications"]
        ), self._pkg_names(result)

    def test_tags_token_simple(self):
        result = search.query_for(model.Package).run(
            {"q": "tags:country-sweden"}
        )
        assert self._check_entity_names(
            result, ["se-publications", "se-opengov"]
        ), self._pkg_names(result)
        result = search.query_for(model.Package).run({"q": "tags:wildlife"})
        assert self._pkg_names(result) == "us-gov-images", self._pkg_names(
            result
        )

    def test_tags_token_with_multi_word_tag(self):
        result = search.query_for(model.Package).run(
            {"q": 'tags:"todo split"'}
        )
        assert self._check_entity_names(
            result, ["us-gov-images"]
        ), self._pkg_names(result)

    def test_tags_token_simple_with_deleted_tag(self):
        # registry has been deleted
        result = search.query_for(model.Package).run({"q": "tags:registry"})
        assert self._pkg_names(result) == "", self._pkg_names(result)

    def test_tags_token_multiple(self):
        result = search.query_for(model.Package).run(
            {"q": "tags:country-sweden tags:format-pdf"}
        )
        assert self._pkg_names(result) == "se-publications", self._pkg_names(
            result
        )
        result = search.query_for(model.Package).run(
            {"q": 'tags:"todo split" tags:war'}
        )
        assert self._pkg_names(result) == "us-gov-images", self._pkg_names(
            result
        )

    def test_tags_token_complicated(self):
        result = search.query_for(model.Package).run(
            {"q": "tags:country-sweden tags:somethingrandom"}
        )
        assert self._pkg_names(result) == "", self._pkg_names(result)

    def test_tags_token_with_capitals(self):
        result = search.query_for(model.Package).run({"q": 'tags:"CAPITALS"'})
        assert self._check_entity_names(
            result, ["se-publications"]
        ), self._pkg_names(result)

    def test_tags_token_with_punctuation(self):
        result = search.query_for(model.Package).run(
            {"q": 'tags:"surprise."'}
        )
        assert self._check_entity_names(
            result, ["se-publications"]
        ), self._pkg_names(result)

    def test_tags_token_with_basic_unicode(self):
        result = search.query_for(model.Package).run(
            {"q": 'tags:"greek omega \u03a9"'}
        )
        assert self._check_entity_names(
            result, ["se-publications"]
        ), self._pkg_names(result)

    def test_pagination(self):
        # large search
        all_results = search.query_for(model.Package).run({"q": self.q_all})
        all_pkgs = all_results["results"]
        all_pkg_count = all_results["count"]

        # limit
        query = {"q": self.q_all, "rows": 2}
        result = search.query_for(model.Package).run(query)
        pkgs = result["results"]
        count = result["count"]
        assert len(pkgs) == 2, pkgs
        assert count == all_pkg_count
        assert pkgs == all_pkgs[:2]

        # offset
        query = {"q": self.q_all, "rows": 2, "start": 2}
        result = search.query_for(model.Package).run(query)
        pkgs = result["results"]
        assert len(pkgs) == 2, pkgs
        assert pkgs == all_pkgs[2:4]

        # larger offset
        query = {"q": self.q_all, "rows": 2, "start": 4}
        result = search.query_for(model.Package).run(query)
        pkgs = result["results"]
        assert len(pkgs) == 2, pkgs
        assert pkgs == all_pkgs[4:6]

    def test_order_by(self):
        # TODO: fix this test
        pytest.skip(
            "as we are not using the 'edismax' query parser now "
            "(requires solr >= 3.*), the search weighting has been changed"
        )
        # large search
        all_results = search.query_for(model.Package).run({"q": self.q_all})
        all_pkgs = all_results["results"]
        all_pkg_count = all_results["count"]

        # rank
        query = {"q": "government", "sort": "rank"}
        result = search.query_for(model.Package).run(query)
        pkgs = result["results"]
        fields = [model.Package.by_name(pkg_name).name for pkg_name in pkgs]
        assert (
            fields[0] == "gils"
        ), fields  # has government in tags, title and notes

        # name
        query = {"q": self.q_all, "sort": "name asc"}
        result = search.query_for(model.Package).run(query)
        pkgs = result["results"]
        fields = [model.Package.by_name(pkg_name).name for pkg_name in pkgs]
        sorted_fields = fields
        sorted_fields.sort()
        assert fields == sorted_fields, repr(fields) + repr(sorted_fields)

        # title
        query = {"q": self.q_all, "sort": "title asc"}
        result = search.query_for(model.Package).run(query)
        pkgs = result["results"]
        fields = [model.Package.by_name(pkg_name).title for pkg_name in pkgs]
        sorted_fields = fields
        sorted_fields.sort()
        assert fields == sorted_fields, repr(fields) + repr(sorted_fields)

        # notes
        query = {"q": self.q_all, "sort": "notes asc"}
        result = search.query_for(model.Package).run(query)
        pkgs = result["results"]
        fields = [model.Package.by_name(pkg_name).notes for pkg_name in pkgs]
        sorted_fields = fields
        sorted_fields.sort()
        assert fields == sorted_fields, repr(fields) + repr(sorted_fields)

        # extra field
        query = {"q": self.q_all, "sort": "date_released asc"}
        result = search.query_for(model.Package).run(query)
        pkgs = result["results"]
        fields = [model.Package.by_name(pkg_name) for pkg_name in pkgs]
        fields = [field.extras.get("date_released") for field in fields]
        sorted_fields = fields
        sorted_fields.sort()
        assert fields == sorted_fields, repr(fields) + repr(sorted_fields)

    def test_search_notes_on(self):
        result = search.query_for(model.Package).run({"q": "restrictions"})
        pkgs = result["results"]
        count = result["count"]
        assert len(pkgs) == 2, pkgs

    def test_search_foreign_chars(self):
        result = search.query_for(model.Package).run({"q": "umlaut"})
        assert result["results"] == ["gils"], result["results"]
        result = search.query_for(model.Package).run({"q": "thumb"})
        assert result["results"] == ["gils"], result["results"]
        result = search.query_for(model.Package).run({"q": "th\xfcmb"})
        assert result["results"] == ["gils"], result["results"]

    def test_groups(self):
        result = search.query_for(model.Package).run({"q": "groups:random"})
        assert self._pkg_names(result) == "", self._pkg_names(result)
        result = search.query_for(model.Package).run({"q": "groups:ukgov"})
        assert result["count"] == 4, self._pkg_names(result)
        result = search.query_for(model.Package).run(
            {"q": "groups:ukgov tags:us"}
        )
        assert result["count"] == 2, self._pkg_names(result)


class TestSearchOverall(object):
    @pytest.fixture(autouse=True)
    def setup_class(self, clean_db, clean_index):
        setup_test_search_index()
        CreateTestData.create()

    def test_overall(self):
        check_search_results("annakarenina", 1, ["annakarenina"])
        check_search_results("warandpeace", 1, ["warandpeace"])
        check_search_results("", 2)

        check_search_results("Tolstoy", 1, ["annakarenina"])
        check_search_results("title:Novel", 1, ["annakarenina"])
        check_search_results("title:peace", 0)
        check_search_results("name:warandpeace", 1)
        check_search_results("groups:david", 2)
        check_search_results("groups:roger", 1)
        check_search_results("groups:lenny", 0)
        check_search_results('tags:"russian"', 2)
        check_search_results('tags:"Flexible \u30a1"', 2)
        check_search_results("Flexible \u30a1", 2)
        check_search_results("Flexible", 2)
        check_search_results("flexible", 2)


class TestGeographicCoverage(object):
    @pytest.fixture(autouse=True)
    def setup_class(self, clean_db, clean_index):
        init_data = [
            {
                "name": "eng",
                "extras": {"geographic_coverage": "100000: England"},
            },
            {
                "name": "eng_ni",
                "extras": {
                    "geographic_coverage": "100100: England, Northern Ireland"
                },
            },
            {
                "name": "uk",
                "extras": {
                    "geographic_coverage": "111100: United Kingdom (England, Scotland, Wales, Northern Ireland"
                },
            },
            {
                "name": "gb",
                "extras": {
                    "geographic_coverage": "111000: Great Britain (England, Scotland, Wales)"
                },
            },
            {"name": "none", "extras": {"geographic_coverage": "000000:"}},
        ]
        CreateTestData.create_arbitrary(init_data)

    def _do_search(self, q, expected_pkgs, count=None):
        query = {"q": q, "sort": "score desc, name asc"}
        result = search.query_for(model.Package).run(query)
        pkgs = result["results"]
        fields = [model.Package.by_name(pkg_name).name for pkg_name in pkgs]
        if not (count is None):
            assert result["count"] == count, result["count"]
        for expected_pkg in expected_pkgs:
            assert expected_pkg in fields, expected_pkg

    def _filtered_search(self, value, expected_pkgs, count=None):
        query = {"q": "geographic_coverage:%s" % value, "sort": "rank"}
        result = search.query_for(model.Package).run(query)
        pkgs = result["results"]
        fields = [model.Package.by_name(pkg_name).name for pkg_name in pkgs]
        if not (count is None):
            assert result["count"] == count, result["count"]
        for expected_pkg in expected_pkgs:
            assert expected_pkg in fields, expected_pkg

    def test_0_basic(self):
        self._do_search("england", ["eng", "eng_ni", "uk", "gb"], 4)
        self._do_search("northern ireland", ["eng_ni", "uk"], 2)
        self._do_search("united kingdom", ["uk"], 1)
        self._do_search("great britain", ["gb"], 1)


class TestExtraFields(object):
    @pytest.fixture(autouse=True)
    def initial_data(self, clean_db, clean_index):
        init_data = [
            {"name": "a", "extras": {"department": "abc", "agency": "ag-a"}},
            {"name": "b", "extras": {"department": "bcd", "agency": "ag-b"}},
            {"name": "c", "extras": {"department": "cde abc"}},
            {"name": "none", "extras": {"department": ""}},
        ]
        CreateTestData.create_arbitrary(init_data)

    def _do_search(self, department, expected_pkgs, count=None):
        result = search.query_for(model.Package).run(
            {"q": "department: %s" % department}
        )
        pkgs = result["results"]
        fields = [model.Package.by_name(pkg_name).name for pkg_name in pkgs]
        if not (count is None):
            assert result["count"] == count, result["count"]
        for expected_pkg in expected_pkgs:
            assert expected_pkg in fields, expected_pkg

    def test_0_basic(self):
        self._do_search("bcd", "b", 1)
        self._do_search('"cde abc"', "c", 1)

    def test_1_extras_in_all_fields(self):
        response = search.query_for(model.Package).run({"q": "abc", "fl": "*"})
        assert response["count"] == 2

        results = response["results"]
        for result in results:
            assert "extras" in result.keys(), result
            assert "department" in result["extras"], result["extras"]
            assert result["extras"]["department"] in [
                "abc",
                "cde abc",
            ], result["extras"]["department"]


class TestRank(object):
    @pytest.fixture(autouse=True)
    def initial_data(self, clean_db, clean_index):
        setup_test_search_index()
        init_data = [
            {
                "name": "test1-penguin-canary",
                "title": "penguin",
                "tags": "canary goose squirrel wombat wombat".split(),
            },
            {
                "name": "test2-squirrel-squirrel-canary-goose",
                "title": "squirrel goose",
                "tags": "penguin wombat".split(),
            },
        ]
        CreateTestData.create_arbitrary(init_data)
        self.pkg_names = [
            "test1-penguin-canary",
            "test2-squirrel-squirrel-canary-goose",
        ]

    def _do_search(self, q, wanted_results):
        query = {"q": q, "sort": "score desc, name asc"}
        result = search.query_for(model.Package).run(query)
        results = result["results"]
        err = "Wanted %r, got %r" % (wanted_results, results)
        assert wanted_results[0] == results[0], err
        assert wanted_results[1] == results[1], err

    def test_0_basic(self):
        self._do_search("wombat", self.pkg_names)
        self._do_search("squirrel", self.pkg_names[::-1])
        self._do_search("canary", self.pkg_names)

    def test_1_weighting(self):
        self._do_search("penguin", self.pkg_names)
        self._do_search("goose", self.pkg_names[::-1])
