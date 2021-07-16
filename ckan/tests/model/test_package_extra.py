# encoding: utf-8

import pytest

from ckan import model
from ckan.tests import helpers, factories


@pytest.mark.usefixtures("clean_db")
class TestPackageExtra(object):
    def test_create_extras(self):
        pkg = model.Package(name="test-package")

        # method 1
        extra1 = model.PackageExtra(key="subject", value="science")
        pkg._extras["subject"] = extra1

        # method 2
        pkg.extras["accuracy"] = "metre"

        model.Session.add_all([pkg])
        model.Session.commit()
        model.Session.remove()

        pkg = model.Package.by_name("test-package")
        assert pkg.extras == {"subject": "science", "accuracy": "metre"}

    def test_delete_extras(self):

        dataset = factories.Dataset(
            extras=[
                {"key": "subject", "value": "science"},
                {"key": "accuracy", "value": "metre"},
            ]
        )
        pkg = model.Package.by_name(dataset["name"])

        del pkg.extras["subject"]
        model.Session.commit()
        model.Session.remove()

        pkg = model.Package.by_name(dataset["name"])
        assert pkg.extras == {"accuracy": "metre"}

    def test_extras_list(self):
        extras = [
            {"key": "subject", "value": "science"},
            {"key": "accuracy", "value": "metre"},
            {"key": "sample_years", "value": "2012-2013"},
        ]
        dataset = factories.Dataset(extras=extras)
        # delete the 'subject' extra
        extras = extras[1:]
        helpers.call_action("package_patch", id=dataset["id"], extras=extras)
        # unrelated extra, to check it doesn't affect things
        factories.Dataset(extras=[{"key": "foo", "value": "bar"}])

        pkg = model.Package.by_name(dataset["name"])
        assert isinstance(pkg.extras_list[0], model.PackageExtra)

        # Extras are removed from database, not just marked as deleted
        assert set(
            [
                (pe.package_id, pe.key, pe.value, pe.state)
                for pe in pkg.extras_list
            ]
        ) == set(
            [
                (dataset["id"], "accuracy", "metre", "active"),
                (dataset["id"], "sample_years", "2012-2013", "active"),
            ]
        )
