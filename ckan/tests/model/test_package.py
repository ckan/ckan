# encoding: utf-8

import pytest

from ckan import model
from ckan.tests import factories


@pytest.mark.usefixtures("clean_db", "with_request_context")
class TestPackage(object):
    def test_create(self):
        # Demonstrate creating a package.
        #
        # In practice this is done by a combination of:
        # * ckan.logic.action.create:package_create
        # * ckan.lib.dictization.model_save.py:package_dict_save
        # etc

        pkg = model.Package(name="test-package")
        pkg.notes = "Some notes"
        pkg.author = "bob"
        pkg.license_id = "odc-by"

        model.Session.add(pkg)
        model.Session.commit()
        model.Session.remove()

        pkg = model.Package.by_name("test-package")
        assert pkg.notes == "Some notes"
        assert pkg.author == "bob"
        assert pkg.license_id == "odc-by"
        assert pkg.license.title == "Open Data Commons Attribution License"

    def test_update(self):
        dataset = factories.Dataset()
        pkg = model.Package.by_name(dataset["name"])

        pkg.author = "bob"
        model.Session.commit()
        model.Session.remove()

        pkg = model.Package.by_name(dataset["name"])
        assert pkg.author == "bob"

    def test_delete(self):
        group = factories.Group()
        dataset = factories.Dataset(
            groups=[{"id": group["id"]}],
            tags=[{"name": "science"}],
            extras=[{"key": "subject", "value": "science"}],
        )
        pkg = model.Package.by_name(dataset["name"])

        pkg.delete()
        model.Session.commit()
        model.Session.remove()

        pkg = model.Package.by_name(dataset["name"])
        assert pkg.state == "deleted"
        # it is removed from the group
        group = model.Group.get(group["id"])
        assert [p.name for p in group.packages()] == []
        # other related objects don't change
        package_extra = model.Session.query(model.PackageExtra).all()[0]
        assert package_extra.state == "active"
        package_tag = model.Session.query(model.PackageTag).all()[0]
        assert package_tag.state == "active"
        tag = model.Session.query(model.Tag).all()[0]
        assert [p.name for p in tag.packages] == [dataset["name"]]

    def test_purge(self):
        org = factories.Organization()
        group = factories.Group()
        dataset = factories.Dataset(
            resources=[
                {
                    "url": "http://example.com/image.png",
                    "format": "png",
                    "name": "Image 1",
                }
            ],
            tags=[{"name": "science"}],
            extras=[{"key": "subject", "value": "science"}],
            groups=[{"id": group["id"]}],
            owner_org=org["id"],
        )
        pkg = model.Package.by_name(dataset["name"])

        pkg.purge()
        model.Session.commit()
        model.Session.remove()

        assert not model.Session.query(model.Package).all()
        # the purge cascades to some objects
        assert not model.Session.query(model.PackageExtra).all()
        assert not model.Session.query(model.PackageTag).all()
        assert not model.Session.query(model.Resource).all()
        # org remains, just not attached to the package
        org = model.Group.get(org["id"])
        assert org.packages() == []
        # tag object remains, just not attached to the package
        tag = model.Session.query(model.Tag).all()[0]
        assert tag.packages == []
        # group object remains, just not attached to the package
        group = model.Group.get(group["id"])
        assert group.packages() == []
