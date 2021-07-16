# encoding: utf-8

import pytest

from ckan import model
from ckan.tests import factories


@pytest.mark.usefixtures("clean_db")
class TestTags(object):
    def test_create_package_with_tags(self):
        pkg = model.Package(name="test-package")

        # method 1
        tag1 = model.Tag(name="science")
        package_tag1 = model.PackageTag(package=pkg, tag=tag1)
        pkg.package_tag_all[:] = [package_tag1]

        # method 2
        tag2 = model.Tag(name="geology")
        package_tag2 = model.PackageTag(package=pkg, tag=tag2)
        pkg.add_tag(tag2)

        # method 3
        pkg.add_tag_by_name("energy")

        model.Session.add_all([pkg, package_tag1, package_tag2])
        model.Session.commit()
        model.Session.remove()

        pkg = model.Package.by_name("test-package")
        assert set([tag.name for tag in pkg.get_tags()]) == set(
            ["science", "geology", "energy"]
        )

    def test_delete_tag(self):
        dataset = factories.Dataset(
            tags=[
                {"name": "science"},
                {"name": "geology"},
                {"name": "energy"},
            ]
        )
        pkg = model.Package.by_name(dataset["name"])

        # method 1 - unused by ckan core
        tag = model.Tag.by_name("science")
        pkg.remove_tag(tag)

        # method 2
        package_tag = (
            model.Session.query(model.PackageTag)
            .join(model.Tag)
            .filter(model.Tag.name == "geology")
            .one()
        )
        package_tag.state = "deleted"

        model.Session.commit()
        model.Session.remove()

        pkg = model.Package.by_name(dataset["name"])
        assert set([tag.name for tag in pkg.get_tags()]) == set(["energy"])
