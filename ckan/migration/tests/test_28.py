from ckan.migration.tests import *

class Test_0_RealData(TestMigrationBase):
    
    @classmethod
    def setup_class(self):
        self.paster('db clean')
        self.setup_db(os.path.join(TEST_DUMPS_PATH, 'test_data_28.pg_dump'))
        self.paster('db upgrade')
        
        
    @classmethod
    def teardown_class(self):
        from ckan import model
        model.Session.close()
        
    