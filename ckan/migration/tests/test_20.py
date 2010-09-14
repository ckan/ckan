from ckan.migration.tests import *

class Test_0_Empty(TestMigrationBase):

    def setup(self):
        self.paster('db clean')
        self.paster('db upgrade')
        self.paster('db init')
        self.paster('create-test-data')
        self.paster('changes commit')

    def teardown(self):
        from ckan import model
        model.Session.close()

    def test_changeset_count(self):        
        from ckan import model
        query = model.Session.query(model.Changeset)
        count = query.count()
        assert count == 2, query.all()


class Test_1_BasicData(TestMigrationBase):

    def setup(self):
        self.paster('db clean')
        # Todo: Create and use 'test_data_19.pg_dump'?
        self.setup_db(os.path.join(TEST_DUMPS_PATH, 'test_data_15.pg_dump'))
        self.paster('db upgrade')
        self.paster('changes commit')

    def teardown(self):
        from ckan import model
        model.Session.close()

    def test_changeset_count(self):        
        from ckan import model
        query = model.Session.query(model.Changeset)
        count = query.count()
        assert count == 2, query.all()

        
class Test_2_RealData(TestMigrationBase):

    def setup(self):
        self.paster('db clean')
        self.setup_db()
        self.paster('db upgrade')
        self.paster('changes commit')

    def test_changeset_count(self):        
        from ckan import model
        query = model.Session.query(model.Changeset)
        count = query.count()
        assert count == 2482, count


