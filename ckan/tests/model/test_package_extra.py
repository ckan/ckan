# encoding: utf-8

import pytest

from ckan import model
from ckan.tests import helpers, factories


@pytest.mark.usefixtures(u"non_clean_db")
class TestPackageExtra(object):
    def test_create_extras(self):
        pkg = model.Package(name=factories.Dataset.stub().name)

        # method 1
        extra1 = model.PackageExtra(key=u"subject", value=u"science")
        pkg._extras[u"subject"] = extra1

        # method 2
        pkg.extras[u"accuracy"] = u"metre"

        model.Session.add_all([pkg])
        model.Session.commit()
        model.Session.remove()

        pkg = model.Package.by_name(pkg.name)
        assert pkg.extras == {u"subject": u"science", u"accuracy": u"metre"}

    def test_delete_extras(self):

        dataset = factories.Dataset(
            extras=[
                {u"key": u"subject", u"value": u"science"},
                {u"key": u"accuracy", u"value": u"metre"},
            ]
        )
        pkg = model.Package.by_name(dataset[u"name"])

        del pkg.extras[u"subject"]
        model.Session.commit()
        model.Session.remove()

        pkg = model.Package.by_name(dataset[u"name"])
        assert pkg.extras == {u"accuracy": u"metre"}

    def test_extras_list(self):
        extras = [
            {u"key": u"subject", u"value": u"science"},
            {u"key": u"accuracy", u"value": u"metre"},
            {u"key": u"sample_years", u"value": u"2012-2013"},
        ]
        dataset = factories.Dataset(extras=extras)
        # delete the 'subject' extra
        extras = extras[1:]
        helpers.call_action(u"package_patch", id=dataset["id"], extras=extras)
        # unrelated extra, to check it doesn't affect things
        factories.Dataset(extras=[{u"key": u"foo", u"value": u"bar"}])

        pkg = model.Package.by_name(dataset[u"name"])
        assert isinstance(pkg.extras_list[0], model.PackageExtra)

        # Extras are removed from database, not just marked as deleted
        assert set(
            [
                (pe.package_id, pe.key, pe.value, pe.state)
                for pe in pkg.extras_list
            ]
        ) == set(
            [
                (dataset["id"], u"accuracy", u"metre", u"active"),
                (dataset["id"], u"sample_years", u"2012-2013", u"active"),
            ]
        )
