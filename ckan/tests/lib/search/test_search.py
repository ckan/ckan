# -*- coding: utf-8 -*-

import os
import pytest

import ckan.config as config
from ckan.lib.search.common import SearchQueryError
import ckan.tests.factories as factories
import ckan.model as model
import ckan.lib.search as search
from ckan.lib.search import check_solr_schema_version, SearchError
from ckan.lib.search.query import _get_local_query_parser

root_dir = os.path.join(os.path.dirname(config.__file__), "solr")
data_dir = os.path.join(os.path.dirname(__file__), "data")


def test_current_schema_exists():
    current_schema = os.path.join(root_dir, "schema.xml")
    assert os.path.exists(current_schema)


def test_check_valid_schema():
    schema_file = os.path.join(root_dir, "schema.xml")
    assert check_solr_schema_version(schema_file)


def test_check_invalid_schema():
    schema_file = os.path.join(data_dir, "schema-no-version.xml")
    with pytest.raises(SearchError) as e:
        check_solr_schema_version(schema_file)
    assert "Could not extract version info" in str(e.value)


def test_check_schema_with_wrong_version():
    schema_file = os.path.join(data_dir, "schema-wrong-version.xml")
    with pytest.raises(SearchError) as e:
        check_solr_schema_version(schema_file)
    assert "SOLR schema version not supported" in str(e.value)


def get_data():
    return {
        "name": "council-owned-litter-bins",
        "extras": [
            {"key": "spatial-reference-system", "value": "test-spatial"},
        ],
    }


@pytest.mark.usefixtures("clean_db", "clean_index")
def test_02_add_package_from_dict():
    factories.Dataset()
    factories.Dataset(**get_data())
    query = search.query_for(model.Package)
    assert query.run({"q": ""})["count"] == 2
    assert query.run({"q": "spatial"})["count"] == 1


@pytest.mark.usefixtures("clean_db", "clean_index")
def test_03_update_package_from_dict():
    factories.Dataset()
    factories.Dataset(**get_data())
    query = search.query_for(model.Package)

    package = model.Package.by_name("council-owned-litter-bins")

    # update package
    package.name = u"new_name"
    extra = model.PackageExtra(key="published_by", value="barrow")
    package._extras[extra.key] = extra
    model.repo.commit_and_remove()

    assert query.run({"q": ""})["count"] == 2
    assert query.run({"q": "barrow"})["count"] == 1
    assert query.run({"q": "barrow"})["results"][0] == "new_name"

    # update package again
    package = model.Package.by_name("new_name")
    package.name = u"council-owned-litter-bins"
    model.repo.commit_and_remove()

    assert query.run({"q": ""})["count"] == 2
    assert query.run({"q": "spatial"})["count"] == 1
    assert (
        query.run({"q": "spatial"})["results"][0]
        == "council-owned-litter-bins"
    )


@pytest.mark.usefixtures("clean_db", "clean_index")
def test_04_delete_package_from_dict():
    factories.Dataset()
    factories.Dataset(**get_data())
    query = search.query_for(model.Package)

    package = model.Package.by_name("council-owned-litter-bins")
    # delete it
    package.delete()
    model.repo.commit_and_remove()

    assert query.run({"q": ""})["count"] == 1


@pytest.mark.parametrize(
    "query,parser",
    [
        ("*:*", ""),
        ("title:test AND organization:test-org", ""),
        ("{!bool must=test}", "bool"),
        (" {!bool must=test}", "bool"),
        ("{!bool must='test string'}", "bool"),
        ("{!bool must='test string'}solr rocks", "bool"),
        (" {!bool must='test string'}solr rocks", "bool"),
        (" {!bool must='test string'}", "bool"),
        ("{!bool must='test string with \"quotes\"'}", "bool"),
        ("{!type=bool must=test}", "bool"),
        ("{!type=bool must='test string'}", "bool"),
        ("{!must=test type=bool}", "bool"),
        ("{!must=test type=bool}solr rocks", "bool"),
        ("{!must='test text' type=bool}solr rocks", "bool"),
        ("{!dismax qf=myfield}solr rocks", "dismax"),
        ("{!type=dismax qf=myfield v='solr rocks'}", "dismax"),
        ("{!type=lucene df=summary}solr rocks", "lucene"),
        ("{!v='lies type= here' type=dismax}", "dismax"),
        ("{!some_parser}", "some_parser"),
        ("{!dismax v=some_value}", "dismax"),
        ("{!some_parser a='0.9' traversalFilter='foo:[*+TO+15]'}", "some_parser"),
        ("{!some_parser must=$ref}", "some_parser"),
    ]

)
def test_get_local_query_parser(query, parser):

    assert _get_local_query_parser(query) == parser


@pytest.mark.parametrize(
    "query",
    [
        "{!v='lies type= here' some params",
        "{!v='lies type= here' v2='\\{some test \\} type=dismax}",
    ]

)
def test_get_local_query_parser_exception(query):

    with pytest.raises(SearchQueryError):
        _get_local_query_parser(query)


def test_local_params_not_allowed_by_default():

    query = search.query_for(model.Package)
    with pytest.raises(search.common.SearchError) as e:
        query.run({"q": "{!bool must=test}"})

    assert str(e.value) == "Local parameters are not supported in param 'q'."


def test_local_params_not_allowed_by_default_different_field():

    query = search.query_for(model.Package)
    with pytest.raises(search.common.SearchError) as e:
        query.run({"fq": "{!bool must=test} +site_id:test.ckan.net"})

    assert str(e.value) == "Local parameters are not supported in param 'fq'."


def test_local_params_not_allowed_by_default_different_field_list():

    query = search.query_for(model.Package)
    with pytest.raises(search.common.SearchError) as e:
        query.run({"fq_list": ["+site_id:default", "{!bool must=test}"]})

    assert str(e.value) == "Local parameters are not supported in param 'fq_list'."


def test_local_params_with_whitespace_not_allowed_by_default():

    query = search.query_for(model.Package)
    with pytest.raises(search.common.SearchError) as e:
        query.run({"q": " {!bool must=test}"})

    assert str(e.value) == "Local parameters are not supported in param 'q'."


@pytest.mark.ckan_config("ckan.search.solr_allowed_query_parsers", "bool")
@pytest.mark.usefixtures("clean_index")
def test_allowed_local_params_via_config_not_defined():

    query = search.query_for(model.Package)
    with pytest.raises(search.common.SearchError) as e:
        query.run({"q": "{!something_else a=test}"})

    assert str(e.value) == "Local parameters are not supported in param 'q'."


@pytest.mark.ckan_config("ckan.search.solr_allowed_query_parsers", "bool knn lucene")
@pytest.mark.usefixtures("clean_index")
def test_allowed_local_params_via_config():
    factories.Dataset(title="A dataset about bees")
    factories.Dataset(title="A dataset about butterflies")
    query = search.query_for(model.Package)

    assert query.run({"q": "{!bool must=bees}", "defType": "lucene"})["count"] == 1

    assert query.run({"q": " {!bool must=bees}", "defType": "lucene"})["count"] == 1

    # Alternative syntax
    assert query.run({"q": "{!type=bool must=beetles}", "defType": "lucene"})["count"] == 0

    assert query.run({"q": "{!must=bees type=bool}", "defType": "lucene"})["count"] == 1

    # Support dot symbol in keys
    assert query.run({"fq": "{!lucene q.op=AND}bees butterflies"})["count"] == 0
    assert query.run({"fq": "{!lucene q.op=OR}bees butterflies"})["count"] == 2
