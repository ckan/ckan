from ckan.migration.tests import *

def _test_family():
    from ckan import model
    rels = model.Package.by_name(u'homer').relationships
    assert len(rels) == 5, len(rels)
    def check(rels, subject, type, object):
        for rel in rels:
            if rel.subject.name == subject and rel.type == type and rel.object.name == object:
                return
        assert 0, 'Could not find relationship in: %r' % rels
    check(rels, 'homer', 'child_of', 'abraham')
    check(rels, 'bart', 'child_of', 'homer')
    check(rels, 'lisa', 'child_of', 'homer')
    check(rels, 'homer_derived', 'derives_from', 'homer')
    check(rels, 'homer', 'depends_on', 'beer')

    rels = model.Package.by_name(u'bart').relationships
    assert len(rels) == 1, len(rels)
    check(rels, 'bart', 'child_of', 'homer')


class Test_0_Empty(TestMigrationBase):
    @classmethod
    def setup_class(self):
        self.paster('db clean')
        self.paster('db upgrade')
        self.paster('db init')
        self.paster('create-test-data family')

    @classmethod
    def teardown_class(self):
        from ckan import model
        model.Session.close()

    def test_package_count(self):        
        from ckan import model
        pkg_query = model.Session.query(model.Package)
        num_pkgs = pkg_query.count()
        assert num_pkgs == 6, pkg_query.count()

    def test_package_details(self):
        _test_family()


class Test_1_BasicData(TestMigrationBase):
    @classmethod
    def setup_class(self):
        self.paster('db clean')
        self.setup_db(os.path.join(TEST_DUMPS_PATH, 'test_data_18.pg_dump'))
        self.paster('db upgrade')

    @classmethod
    def teardown_class(self):
        from ckan import model
        model.Session.close()

    def test_package_count(self):        
        from ckan import model
        pkg_query = model.Session.query(model.Package)
        num_pkgs = pkg_query.count()
        assert num_pkgs == 6, pkg_query.all()

    def test_package_details(self):
        _test_family()
        
    def test_ids(self):
        from ckan import model
        uuid_length = 36
        obj = model.Session.query(model.Package).first()
        assert len(obj.id) == uuid_length, obj.id
        obj = model.Session.query(model.Tag).first()
        assert len(obj.id) == uuid_length, obj.id
        obj = model.Session.query(model.PackageTag).first()
        assert len(obj.id) == uuid_length, obj.id
        obj = model.Session.query(model.PackageExtra).first()
        assert len(obj.id) == uuid_length, obj.id
        obj = model.Session.query(model.PackageRevision).first()
        assert len(obj.id) == uuid_length, obj.id
        obj = model.Session.query(model.PackageTagRevision).first()
        assert len(obj.id) == uuid_length, obj.id
        obj = model.Session.query(model.PackageExtraRevision).first()
        assert len(obj.id) == uuid_length, obj.id
