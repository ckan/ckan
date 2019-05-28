# encoding: utf-8

from nose.tools import assert_equal

from ckan import model
from ckan.tests import helpers, factories


class TestPackage(object):

    def setup(self):
        helpers.reset_db()

    def test_create(self):
        # Demonstrate creating a package.
        #
        # In practice this is done by a combination of:
        # * ckan.logic.action.create:package_create
        # * ckan.lib.dictization.model_save.py:package_dict_save
        # etc

        model.repo.new_revision()

        pkg = model.Package(name=u'test-package')
        pkg.notes = u'Some notes'
        pkg.author = u'bob'
        pkg.license_id = u'odc-by'

        model.Session.add(pkg)
        model.Session.commit()
        model.Session.remove()

        pkg = model.Package.by_name(u'test-package')
        assert_equal(pkg.notes, u'Some notes')
        assert_equal(pkg.author, u'bob')
        assert_equal(pkg.license_id, u'odc-by')
        assert_equal(pkg.license.title,
                     u'Open Data Commons Attribution License')

    def test_update(self):
        dataset = factories.Dataset()
        pkg = model.Package.by_name(dataset['name'])

        model.repo.new_revision()
        pkg.author = u'bob'
        model.Session.commit()
        model.Session.remove()

        pkg = model.Package.by_name(dataset['name'])
        assert_equal(pkg.author, u'bob')

    def test_delete(self):
        group = factories.Group()
        dataset = factories.Dataset(
            groups=[{u'id': group['id']}],
            tags=[{u'name': u'science'}],
            extras=[{u'key': u'subject', u'value': u'science'}],
        )
        pkg = model.Package.by_name(dataset['name'])

        model.repo.new_revision()
        pkg.delete()
        model.Session.commit()
        model.Session.remove()

        pkg = model.Package.by_name(dataset['name'])
        assert_equal(pkg.state, u'deleted')
        # it is removed from the group
        group = model.Group.get(group['id'])
        assert_equal([p.name for p in group.packages()], [])
        # other related objects don't change
        package_extra = model.Session.query(model.PackageExtra).all()[0]
        assert_equal(package_extra.state, u'active')
        package_tag = model.Session.query(model.PackageTag).all()[0]
        assert_equal(package_tag.state, u'active')
        tag = model.Session.query(model.Tag).all()[0]
        assert_equal([p.name for p in tag.packages], [dataset['name']])

    def test_purge(self):
        org = factories.Organization()
        group = factories.Group()
        dataset = factories.Dataset(
            resources=[{u'url': u'http://example.com/image.png',
                        u'format': u'png', u'name': u'Image 1'}],
            tags=[{u'name': u'science'}],
            extras=[{u'key': u'subject', u'value': u'science'}],
            groups=[{u'id': group['id']}],
            owner_org=org['id'],
        )
        pkg = model.Package.by_name(dataset['name'])

        model.repo.new_revision()
        pkg.purge()
        model.Session.commit()
        model.Session.remove()

        assert not model.Session.query(model.Package).all()
        # the purge cascades to some objects
        assert not model.Session.query(model.PackageExtra).all()
        assert not model.Session.query(model.PackageTag).all()
        assert not model.Session.query(model.Resource).all()
        # org remains, just not attached to the package
        org = model.Group.get(org['id'])
        assert_equal(org.packages(), [])
        # tag object remains, just not attached to the package
        tag = model.Session.query(model.Tag).all()[0]
        assert_equal(tag.packages, [])
        # group object remains, just not attached to the package
        group = model.Group.get(group['id'])
        assert_equal(group.packages(), [])
