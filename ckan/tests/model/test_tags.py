# encoding: utf-8

import pytest

from ckan import model
from ckan.tests import factories


@pytest.mark.usefixtures(u"non_clean_db")
class TestTags(object):
    def test_create_package_with_tags(self):
        pkg = model.Package(name=factories.Dataset.stub().name)

        # method 1
        tag1 = model.Tag(name=factories.Tag.stub().name)
        package_tag1 = model.PackageTag(package=pkg, tag=tag1)
        pkg.package_tags[:] = [package_tag1]

        # method 2
        tag2 = model.Tag(name=factories.Tag.stub().name)
        package_tag2 = model.PackageTag(package=pkg, tag=tag2)
        pkg.add_tag(tag2)

        # method 3
        pkg.add_tag_by_name(u"energy")

        model.Session.add_all([pkg, package_tag1, package_tag2])
        model.Session.commit()
        model.Session.remove()

        pkg = model.Package.by_name(pkg.name)
        assert set([tag.name for tag in pkg.get_tags()]) == set(
            [tag1.name, tag2.name, u"energy"]
        )

    def test_delete_tag(self):
        tag_name1 = factories.Tag.stub().name
        tag_name2 = factories.Tag.stub().name
        tag_name3 = factories.Tag.stub().name

        dataset = factories.Dataset(
            tags=[
                {u"name": tag_name1},
                {u"name": tag_name2},
                {u"name": tag_name3},
            ]
        )
        pkg = model.Package.by_name(dataset[u"name"])

        # method 1 - unused by ckan core
        tag = model.Tag.by_name(tag_name1)
        pkg.remove_tag(tag)

        # method 2
        package_tag = (
            model.Session.query(model.PackageTag)
            .join(model.Tag)
            .filter(model.Tag.name == tag_name2)
            .one()
        )
        package_tag.state = u"deleted"

        model.Session.commit()
        model.Session.remove()

        pkg = model.Package.by_name(dataset[u"name"])
        tags = set([tag.name for tag in pkg.get_tags()])
        assert tag_name3 in tags
        assert tag_name1 not in tags
        assert tag_name2 not in tags
