# encoding: utf-8

from nose.tools import assert_equal

from ckan import model
from ckan.tests import helpers, factories


class TestPackage(object):

    def setup(self):
        helpers.reset_db()

    def test_create_package_with_tags(self):
        model.repo.new_revision()

        pkg = model.Package(name=u'test-package')

        # method 1
        tag1 = model.Tag(name=u'science')
        package_tag1 = model.PackageTag(package=pkg, tag=tag1)
        pkg.package_tag_all[:] = [package_tag1]

        # method 2
        tag2 = model.Tag(name=u'geology')
        package_tag2 = model.PackageTag(package=pkg, tag=tag2)
        pkg.add_tag(tag2)

        # method 3
        pkg.add_tag_by_name(u'energy')

        model.Session.add_all([pkg, package_tag1, package_tag2])
        model.Session.commit()
        model.Session.remove()

        pkg = model.Package.by_name(u'test-package')
        assert_equal(
            set([tag.name for tag in pkg.get_tags()]),
            set([u'science', u'geology', u'energy'])
        )

    def test_delete_tag(self):
        dataset = factories.Dataset(tags=[{u'name': u'science'},
                                          {u'name': u'geology'},
                                          {u'name': u'energy'}])
        pkg = model.Package.by_name(dataset['name'])

        model.repo.new_revision()

        # method 1 - unused by ckan core
        tag = model.Tag.by_name(u'science')
        pkg.remove_tag(tag)

        # method 2
        package_tag = \
            model.Session.query(model.PackageTag) \
            .join(model.Tag) \
            .filter(model.Tag.name == u'geology') \
            .one()
        package_tag.state = u'deleted'

        model.Session.commit()
        model.Session.remove()

        pkg = model.Package.by_name(dataset['name'])
        assert_equal(
            set([tag.name for tag in pkg.get_tags()]),
            set(['energy'])
        )
