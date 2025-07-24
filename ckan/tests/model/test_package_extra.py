# encoding: utf-8

import pytest

from ckan import model
from ckan.tests import factories


@pytest.mark.usefixtures(u"non_clean_db")
class TestPackageExtra(object):
    def test_create_extras(self):
        pkg = model.Package(name=factories.Dataset.stub().name)

        pkg.extras = {"accuracy": "metre"}

        model.Session.add_all([pkg])
        model.Session.commit()
        model.Session.remove()

        pkg = model.Package.by_name(pkg.name)
        assert pkg.extras == {"accuracy": "metre"}

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
