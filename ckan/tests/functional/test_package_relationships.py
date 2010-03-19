from ckan.tests import *
import ckan.model as model
from ckan.lib.create_test_data import CreateTestData

class TestRelationships(TestController):
    @classmethod
    def setup_class(self):
        create = CreateTestData
        create.create_arbitrary([{'name':u'abraham', 'title':u'Abraham'},
                                 {'name':u'homer', 'title':u'Homer'},
                                 {'name':u'homer_derived', 'title':u'Homer Derived'},
                                 {'name':u'beer', 'title':u'Beer'},
                                 {'name':u'bart', 'title':u'Bart'},
                                 {'name':u'lisa', 'title':u'Lisa'},
                                 ])
        def pkg(pkg_name):
            return model.Package.by_name(unicode(pkg_name))
        model.repo.new_revision()
        pkg('abraham').add_relationship(u'parent_of', pkg('homer'))
        pkg('homer').add_relationship(u'parent_of', pkg('bart'))
        pkg('homer').add_relationship(u'parent_of', pkg('lisa'))
        pkg('homer_derived').add_relationship(u'derives_from', pkg('homer'))
        pkg('homer').add_relationship(u'depends_on', pkg('beer'))
        model.repo.commit_and_remove()

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()

    def test_read_package(self):
        def read_package(pkg_name):
            offset = url_for(controller='package', action='read', id=pkg_name)
            res = self.app.get(offset)
            assert 'Packages - %s' % pkg_name in res
            return res
        res = read_package(u'homer')
        self.check_named_element(res, 'li', 'is a child of', 'abraham')
        self.check_named_element(res, 'li', 'is a child of', '<a href="/package/abraham">abraham</a>')
        self.check_named_element(res, 'li', 'is a parent of', 'bart')
        self.check_named_element(res, 'li', 'is a parent of', 'lisa')
        self.check_named_element(res, 'li', 'has derivation', 'homer_derived')
        self.check_named_element(res, 'li', 'depends on', 'beer')
        
        res = read_package(u'bart')
        self.check_named_element(res, 'li', 'has sibling', 'lisa')
        self.check_named_element(res, 'li', 'is a child of', 'homer')

        res = read_package(u'lisa')
        self.check_named_element(res, 'li', 'has sibling', 'bart')
