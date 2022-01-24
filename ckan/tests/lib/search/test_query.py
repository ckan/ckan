# -*- coding: utf-8 -*-

import pytest
import ckan.model as model
import ckan.lib.search as search
import ckan.tests.factories as factories
from ckan.lib.create_test_data import CreateTestData


@pytest.mark.usefixtures("clean_db", "clean_index")
class TestTagQuery(object):
    def create_test_data(self):
        factories.Dataset(tags=[{"name": "russian"}, {"name": "tolstoy"}])
        factories.Dataset(tags=[{"name": "Flexible \u30a1"}])

    def test_good_search_query(self):
        self.create_test_data()
        result = search.query_for(model.Tag).run(query=u"ru")
        assert result["count"] == 1, result
        assert "russian" in result["results"]

        result = search.query_for(model.Tag).run(query=u"s")
        assert result["count"] == 2, result
        assert "russian" in result["results"]
        assert "tolstoy" in result["results"]

    def test_good_search_queries(self):
        self.create_test_data()
        result = search.query_for(model.Tag).run(query=[u"ru", u"s"])
        assert result["count"] == 1, result
        assert "russian" in result["results"], result

    def test_bad_search_query(self):
        self.create_test_data()
        result = search.query_for(model.Tag).run(query=u"asdf")
        assert result["count"] == 0, result

    def test_search_with_capital_letter_in_tagname(self):
        self.create_test_data()
        """
        Asserts that it doesn't matter if the tagname has capital letters in it.
        """
        result = search.query_for(model.Tag).run(query=u"lexible")
        assert u"Flexible \u30a1" in result["results"]

    def test_search_with_capital_letter_in_search_query(self):
        self.create_test_data()
        """
        Asserts that search works with a capital letter in the search query.
        """
        result = search.query_for(model.Tag).run(query=u"Flexible")
        assert u"Flexible \u30a1" in result["results"]

    def test_search_with_unicode_in_search_query(self):
        self.create_test_data()
        """
        Asserts that search works with a unicode character above \u00ff.
        """
        result = search.query_for(model.Tag).run(query=u" \u30a1")
        assert u"Flexible \u30a1" in result["results"]

    def test_search_is_case_insensitive(self):
        self.create_test_data()
        result = search.query_for(model.Tag).run(query=u"flexible")
        assert u"Flexible \u30a1" in result["results"]

    def test_good_search_fields(self):
        self.create_test_data()
        result = search.query_for(model.Tag).run(fields={"tags": u"ru"})
        assert result["count"] == 1, result
        assert "russian" in result["results"], result

        result = search.query_for(model.Tag).run(fields={"tags": u"s"})
        assert result["count"] == 2, result
        assert "russian" in result["results"], result
        assert "tolstoy" in result["results"], result

    def test_bad_search_fields(self):
        self.create_test_data()
        result = search.query_for(model.Tag).run(fields={"tags": u"asdf"})
        assert result["count"] == 0, result


@pytest.fixture
def resources_for_search():
    pkg1 = factories.Dataset(name="pkg1")
    pkg2 = factories.Dataset()
    factories.Resource(
        url=TestResourceQuery.ab,
        description="This is site ab.",
        alt_url="alt_1",
        format="Excel spreadsheet",
        hash="xyz-123",
        package_id=pkg1["id"],
    )
    factories.Resource(
        url=TestResourceQuery.cd,
        description="This is site cd.",
        alt_url="alt_2",
        format="Office spreadsheet",
        hash="qwe-456",
        package_id=pkg1["id"],
    )

    factories.Resource(
        url=TestResourceQuery.cd,
        description="This is site cd.",
        alt_url="alt_1",
        package_id=pkg2["id"],
    )
    factories.Resource(
        url=TestResourceQuery.ef, description="This is site ef.", package_id=pkg2["id"]
    )
    factories.Resource(
        url=TestResourceQuery.ef, description="This is site gh.", package_id=pkg2["id"]
    )
    factories.Resource(
        url=TestResourceQuery.ef, description="This is site ij.", package_id=pkg2["id"]
    )


@pytest.mark.usefixtures("clean_db", "clean_index", "resources_for_search")
class TestResourceQuery(object):
    ab = "http://site.com/a/b.txt"
    cd = "http://site.com/c/d.txt"
    ef = "http://site.com/e/f.txt"

    def res_search(
        self, query="", fields={}, terms=[], options=search.QueryOptions()
    ):
        result = search.query_for(model.Resource).run(
            query=query, fields=fields, terms=terms, options=options
        )
        resources = [
            model.Session.query(model.Resource).get(resource_id)
            for resource_id in result["results"]
        ]
        urls = set([resource.url for resource in resources])
        return urls

    def test_search_url(self):
        fields = {"url": "site.com"}
        result = search.query_for(model.Resource).run(fields=fields)
        assert result["count"] == 6
        resources = [
            model.Session.query(model.Resource).get(resource_id)
            for resource_id in result["results"]
        ]
        urls = set([resource.url for resource in resources])
        assert set([self.ab, self.cd, self.ef]) == urls

    def test_search_url_2(self):
        urls = self.res_search(fields={"url": "a/b"})
        assert set([self.ab]) == urls, urls

    def test_search_url_multiple_words(self):
        fields = {"url": "e f"}
        urls = self.res_search(fields=fields)
        assert {self.ef} == urls

    def test_search_url_none(self):
        urls = self.res_search(fields={"url": "nothing"})
        assert set() == urls, urls

    def test_search_description(self):
        urls = self.res_search(fields={"description": "cd"})
        assert set([self.cd]) == urls, urls

    def test_search_format(self):
        urls = self.res_search(fields={"format": "excel"})
        assert set([self.ab]) == urls, urls

    def test_search_format_2(self):
        urls = self.res_search(fields={"format": "sheet"})
        assert set([self.ab, self.cd]) == urls, urls

    def test_search_hash_complete(self):
        urls = self.res_search(fields={"hash": "xyz-123"})
        assert set([self.ab]) == urls, urls

    def test_search_hash_partial(self):
        urls = self.res_search(fields={"hash": "xyz"})
        assert set([self.ab]) == urls, urls

    def test_search_hash_partial_but_not_initial(self):
        urls = self.res_search(fields={"hash": "123"})
        assert set() == urls, urls

    def test_search_several_fields(self):
        urls = self.res_search(fields={"description": "ab", "format": "sheet"})
        assert set([self.ab]) == urls, urls

    def test_search_all_fields(self):
        fields = {"url": "a/b"}
        options = search.QueryOptions(all_fields=True)
        result = search.query_for(model.Resource).run(
            fields=fields, options=options
        )
        assert result["count"] == 1, result
        res_dict = result["results"][0]
        assert isinstance(res_dict, dict)
        res_keys = set(res_dict.keys())
        expected_res_keys = set(model.Resource.get_columns())
        expected_res_keys.update(
            ["id", "package_id", "position"]
        )
        assert res_keys == expected_res_keys
        pkg1 = model.Package.by_name(u"pkg1")
        ab = [r for r in pkg1.resources if r.url == self.ab][0]
        assert res_dict["id"] == ab.id
        assert res_dict["package_id"] == pkg1.id
        assert res_dict["url"] == ab.url
        assert res_dict["description"] == ab.description
        assert res_dict["format"] == ab.format
        assert res_dict["hash"] == ab.hash
        assert res_dict["position"] == 0

    def test_pagination(self):
        # large search
        options = search.QueryOptions(order_by="id")
        fields = {"url": "site"}
        all_results = search.query_for(model.Resource).run(
            fields=fields, options=options
        )
        all_resources = all_results["results"]
        all_resource_count = all_results["count"]
        assert all_resource_count >= 6, all_results

        # limit
        options = search.QueryOptions(order_by="id")
        options.limit = 2
        result = search.query_for(model.Resource).run(
            fields=fields, options=options
        )
        resources = result["results"]
        count = result["count"]
        assert len(resources) == 2, resources
        assert count == all_resource_count, (count, all_resource_count)
        assert resources == all_resources[:2], "%r, %r" % (
            resources,
            all_resources,
        )

        # offset
        options = search.QueryOptions(order_by="id")
        options.limit = 2
        options.offset = 2
        result = search.query_for(model.Resource).run(
            fields=fields, options=options
        )
        resources = result["results"]
        assert len(resources) == 2, resources
        assert resources == all_resources[2:4]

        # larger offset
        options = search.QueryOptions(order_by="id")
        options.limit = 2
        options.offset = 4
        result = search.query_for(model.Resource).run(
            fields=fields, options=options
        )
        resources = result["results"]
        assert len(resources) == 2, resources
        assert resources == all_resources[4:6]

    def test_extra_info(self):
        fields = {"alt_url": "alt_1"}
        result = search.query_for(model.Resource).run(fields=fields)
        assert result["count"] == 2, result

        fields = {"alt_url": "alt_2"}
        result = search.query_for(model.Resource).run(fields=fields)
        assert result["count"] == 1, result


def test_convert_legacy_params_to_solr():
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
    assert convert({"tags": [u"with greek omega \u03a9"]}) == {
        "q": u'tags:"with greek omega \u03a9"'
    }
    assert convert({"tags": ["tolstoy"]}) == {"q": 'tags:"tolstoy"'}
    assert convert({"tags": "tolstoy"}) == {"q": 'tags:"tolstoy"'}
    assert convert({"tags": "more than one tolstoy"}) == {
        "q": 'tags:"more than one tolstoy"'
    }
    assert convert({"tags": u"with greek omega \u03a9"}) == {
        "q": u'tags:"with greek omega \u03a9"'
    }
    assert convert({"title": "Seymour: An Introduction"}) == {
        "q": r'title:"Seymour\: An Introduction"'
    }
    assert convert({"title": "Pop!"}) == {"q": r"title:Pop\!"}

    with pytest.raises(search.SearchError):
        convert({"tags": {"tolstoy": 1}})


@pytest.mark.usefixtures("clean_db", "clean_index")
class TestPackageQuery:
    def test_all_records_by_shared_notes(self):
        pkg1 = factories.Dataset(notes="shared")
        pkg2 = factories.Dataset(notes="shared")
        pkg3 = factories.Dataset(notes="shared")
        result = search.query_for(model.Package).run({"q": "shared"})
        assert {pkg1["name"], pkg2["name"], pkg3["name"]} == set(result["results"])

    def test_single_by_name(self):
        factories.Dataset(name="first")
        factories.Dataset(name="second")

        result = search.query_for(model.Package).run({"q": u"first"})
        assert result["results"] == ["first"]

    def test_name_multiple_results(self):
        factories.Dataset(name="first-record")
        factories.Dataset(name="second-record")
        factories.Dataset(name="third-dataset")
        result = search.query_for(model.Package).run({"q": u"record"})
        assert set(result["results"]) == {"first-record", "second-record"}

    def test_title_token(self):
        pkg1 = factories.Dataset(title="first record")
        pkg2 = factories.Dataset(title="second record")
        factories.Dataset(title="third dataset")

        result = search.query_for(model.Package).run({"q": u"title:record"})
        assert set(result["results"]) == {pkg1["name"], pkg2["name"]}

    def test_not_real_license(self):
        factories.Dataset()
        result = search.query_for(model.Package).run(
            {"q": u'license:"OKD::Other (PublicsDomain)"'}
        )
        assert result["count"] == 0, result

    def test_quotation(self):
        pkg1 = factories.Dataset(title="Government Expenditure")
        factories.Dataset(title="Government Extra Expenditure")
        # multiple words quoted
        result = search.query_for(model.Package).run(
            {"q": u'"Government Expenditure"'}
        )
        assert [pkg1["name"]] == result["results"]

        # multiple words quoted wrong order
        result = search.query_for(model.Package).run(
            {"q": u'"Expenditure Government"'}
        )
        assert result["results"] == []

    def test_tags_field_split_word(self):
        pkg1 = factories.Dataset(tags=[{"name": "split todo"}])
        result = search.query_for(model.Package).run({"q": u"todo split"})
        assert result["results"] == [pkg1["name"]]

    def test_tags_field_with_capitals(self):
        pkg1 = factories.Dataset(tags=[{"name": "capitals"}])
        result = search.query_for(model.Package).run({"q": u"CAPITALS"})
        assert result["results"] == [pkg1["name"]]

    def dont_test_tags_field_with_basic_unicode(self):
        pkg1 = factories.Dataset(tags=[{"name": "greek omega \u03a9"}])
        result = search.query_for(model.Package).run(
            {"q": u"greek omega \u03a9"}
        )
        assert result["results"] == [pkg1["name"]]

    def test_tags_token_simple(self):
        pkg1 = factories.Dataset(tags=[{"name": "country-sweden"}])
        result = search.query_for(model.Package).run(
            {"q": u"tags:country-sweden"}
        )
        assert result["results"] == [pkg1["name"]]

    def test_tags_token_with_multi_word_tag(self):
        pkg1 = factories.Dataset(tags=[{"name": "todo split"}])
        result = search.query_for(model.Package).run(
            {"q": u'tags:"todo split"'}
        )
        assert result["results"] == [pkg1["name"]]

    def test_tags_token_multiple(self):
        pkg1 = factories.Dataset(tags=[{"name": "country-sweden"}, {"name": "format-pdf"}])
        result = search.query_for(model.Package).run(
            {"q": u"tags:country-sweden tags:format-pdf"}
        )
        assert result["results"] == [pkg1["name"]]
        result = search.query_for(model.Package).run(
            {"q": u'tags:"todo split" tags:war'}
        )

    def test_tags_token_with_punctuation(self):
        pkg1 = factories.Dataset(tags=[{"name": "surprise."}])
        result = search.query_for(model.Package).run(
            {"q": u'tags:"surprise."'}
        )
        assert result["results"] == [pkg1["name"]]

    def test_overall(self):
        CreateTestData.create()
        query = search.query_for(model.Package)
        assert query.run({"q": "annakarenina"})["count"] == 1
        assert query.run({"q": "warandpeace"})["count"] == 1
        assert query.run({"q": ""})["count"] == 2

        assert query.run({"q": "Tolstoy"})["count"] == 1
        assert query.run({"q": "title:Novel"})["count"] == 1
        assert query.run({"q": "title:peace"})["count"] == 0
        assert query.run({"q": "name:warandpeace"})["count"] == 1
        assert query.run({"q": "groups:david"})["count"] == 2
        assert query.run({"q": "groups:roger"})["count"] == 1
        assert query.run({"q": "groups:lenny"})["count"] == 0
        assert query.run({"q": 'tags:"russian"'})["count"] == 2
        assert query.run({"q": 'tags:"Flexible \u30a1"'})["count"] == 2
        assert query.run({"q": "Flexible \u30a1"})["count"] == 2
        assert query.run({"q": "Flexible"})["count"] == 2
        assert query.run({"q": "flexible"})["count"] == 2
