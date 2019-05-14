# encoding: utf-8

from nose.tools import assert_equal

from ckan import model
from ckan.tests import helpers, factories


class TestPackage(object):

    def setup(self):
        helpers.reset_db()

    def test_create_extras(self):
        model.repo.new_revision()

        pkg = model.Package(name=u'test-package')

        # method 1
        extra1 = model.PackageExtra(key=u'subject', value=u'science')
        pkg._extras[u'subject'] = extra1

        # method 2
        pkg.extras[u'accuracy'] = u'metre'

        model.Session.add_all([pkg])
        model.Session.commit()
        model.Session.remove()

        pkg = model.Package.by_name(u'test-package')
        assert_equal(
            pkg.extras,
            {u'subject': u'science',
             u'accuracy': u'metre'}
        )

    def test_delete_extras(self):

        dataset = factories.Dataset(extras=[
            {u'key': u'subject', u'value': u'science'},
            {u'key': u'accuracy', u'value': u'metre'}]
        )
        pkg = model.Package.by_name(dataset['name'])

        model.repo.new_revision()
        del pkg.extras[u'subject']
        model.Session.commit()
        model.Session.remove()

        pkg = model.Package.by_name(dataset['name'])
        assert_equal(
            pkg.extras,
            {u'accuracy': u'metre'}
        )
