from ckan.tests import *
import ckan.model as model
from ckan.lib.create_test_data import CreateTestData
from base import FunctionalTestCase

class TestRelationships(FunctionalTestCase):
    @classmethod
    def setup_class(self):
        create = CreateTestData
        create.create_family_test_data()

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()

    def test_read_package(self):
        def read_package(pkg_name):
            offset = url_for(controller='package', action='read', id=pkg_name)
            res = self.app.get(offset)
            pkg = model.Package.by_name(pkg_name)
            assert '%s - Datasets' % pkg.title in res
            return res
        res = read_package(u'homer')
        self.check_named_element(res, 'li', 'is a child of', 'abraham')
        self.check_named_element(res, 'li', 'is a child of', '<a href="/dataset/abraham">abraham</a>')
        self.check_named_element(res, 'li', 'is a parent of', 'bart')
        self.check_named_element(res, 'li', 'is a parent of', 'lisa')
        self.check_named_element(res, 'li', 'has derivation', 'homer_derived')
        self.check_named_element(res, 'li', 'depends on', 'beer')
        
        res = read_package(u'bart')
        self.check_named_element(res, 'li', 'has sibling', 'lisa')
        self.check_named_element(res, 'li', 'is a child of', 'homer')

        res = read_package(u'lisa')
        self.check_named_element(res, 'li', 'has sibling', 'bart')
