# -*- coding: utf-8 -*-

import os
import pytest

import ckan.config as config
import ckan.tests.factories as factories
import ckan.model as model
import ckan.lib.search as search
from ckan.lib.search import check_solr_schema_version, SearchError

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
