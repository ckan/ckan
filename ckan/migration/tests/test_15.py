from ckan.migration.tests import *

class Test15(TestMigrationBase):
    @classmethod
    def setup_class(self):
        self.setup_db()

    def test_complex(self):
        self.run('paster db --config %s upgrade' % CONFIG_FILE)
        self.run(self.psqlbase + ' -c "select count(*) from package_resource_revision;"')
        self.run(self.psqlbase + ' -c "select count(*) from package_resource;"')
        self.run(self.psqlbase + ' -c "select * from package_resource join package_resource_revision on package_resource.id = package_resource_revision.continuity_id limit 2;"')

    def test_simple(self):
        cmd = 'paster db clean && paster db upgrade && paster db init && paster create-test-data'
        print(cmd)
        print('nosetests ckan/tests/model')

