from ckan.migration.tests import *

def _test_anna():
    from ckan import model
    pkg_query = model.Session.query(model.Package)
    num_pkgs = pkg_query.count()
    assert num_pkgs == 2, pkg_query.all()
    anna = model.Package.by_name(u'annakarenina')
    assert anna.title == u'A Novel By Tolstoy', anna.title
    
class Test_0_Empty(TestMigrationBase):
    @classmethod
    def setup_class(self):
        self.paster('db clean')
        self.paster('db upgrade')
        self.paster('db init')
        self.paster('create-test-data')

    @classmethod
    def teardown_class(self):
        from ckan import model
        model.Session.close()

    def test_package_details(self):
        _test_anna()

        from ckan import model
        anna = model.Package.by_name(u'annakarenina')
        assert not anna.relationships, anna.relationships

class Test_1_BasicData(TestMigrationBase):
    @classmethod
    def setup_class(self):
        self.setup_db(os.path.join(TEST_DUMPS_PATH, 'test_data_16.pg_dump'))
        # This dump was created on a v.16 repo with something like this:
        # $ paster db clean && paster db init && paster create-test-data
        # $ export PGPASSWORD=pass&&pg_dump -U tester -D ckantest -h localhost > ../ckan/ckan/migration/tests/test_dumps/test_data_16.pg_dump
        self.paster('db upgrade')

    @classmethod
    def teardown_class(self):
        from ckan import model
        model.Session.close()

    def test_package_details(self):
        _test_anna()

    def test_relationships(self):
        from ckan import model
        anna = model.Package.by_name(u'annakarenina')
        assert not anna.relationships, anna.relationships
        war = model.Package.by_name(u'warandpeace')
        anna.add_relationship('parent_of', war, u'Some comment')
        rev = model.repo.new_revision()
        model.repo.commit_and_remove()

        anna = model.Package.by_name(u'annakarenina')
        assert len(anna.relationships) == 1, anna.relationships
        rel = anna.relationships[0]
        assert rel.type == u'child_of'
        assert rel.object == anna, rel.object
        assert rel.subject.name == u'warandpeace', rel.subject
