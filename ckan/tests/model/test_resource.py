# encoding: utf-8

import pytest
from sqlalchemy.exc import IntegrityError

import ckan.model as model
import ckan.tests.factories as factories

Resource = model.Resource


@pytest.mark.usefixtures("non_clean_db")
class TestResource(object):
    def test_edit_url(self):
        res_dict = factories.Resource(url="http://first")
        res = Resource.get(res_dict["id"])
        res.url = "http://second"
        model.repo.commit_and_remove()
        res = Resource.get(res_dict["id"])
        assert res.url == "http://second"

    def test_edit_extra(self):
        res_dict = factories.Resource(newfield="first")
        res = Resource.get(res_dict["id"])
        res.extras = {"newfield": "second"}
        model.repo.commit_and_remove()
        res = Resource.get(res_dict["id"])
        assert res.extras["newfield"] == "second"

    def test_resource_count(self):
        """Resource.count() should return a count of instances of Resource
        class"""
        initial = Resource.count()
        factories.Resource()
        factories.Resource()
        factories.Resource()
        assert Resource.count() == initial + 3

    def test_package_deletion_does_not_delete_resources(self):
        parent = factories.Dataset()
        initial = model.Resource.active().count()
        factories.Resource(package_id=parent["id"])
        factories.Resource(package_id=parent["id"])

        assert model.Resource.active().count() == initial + 2

        pkg = model.Package.get(parent["id"])
        pkg.delete()
        model.repo.commit_and_remove()

        assert model.Resource.active().count() == initial + 2

    def test_package_purge_deletes_resources(self):
        parent = factories.Dataset()
        initial = model.Resource.active().count()
        factories.Resource(package_id=parent["id"])
        factories.Resource(package_id=parent["id"])

        pkg = model.Package.get(parent["id"])
        pkg.purge()
        model.repo.commit_and_remove()

        assert model.Resource.active().count() == initial

    def test_resource_unique_positions(self):
        """
        Position values should be unique per dataset.
        """
        parent = factories.Dataset()
        factories.Resource(package_id=parent["id"])
        res2 = factories.Resource(package_id=parent["id"])

        res2.position = 0

        with pytest.raises(IntegrityError) as e:
            model.Session.add(res2)
            model.Session.commit()

        err = e.value
        assert 'duplicate key value violates unique constraint "con_package_resource_unique_position"' in str(err)
