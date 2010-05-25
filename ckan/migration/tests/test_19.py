from ckan.migration.tests import *

def _test_family():
    from ckan import model
    rels = model.Package.by_name(u'homer').get_relationships(active=False)
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

    rels = model.Package.by_name(u'bart').get_relationships(active=False)
    assert len(rels) == 1, len(rels)
    check(rels, 'bart', 'child_of', 'homer')

def _homer_to_bart_rels(active=True):
    from ckan import model
    return model.Package.by_name(u'homer').get_relationships_with(model.Package.by_name(u'bart'), active=active)

def _test_delete():
    from ckan import model
    rels = _homer_to_bart_rels()
    assert len(rels) == 1

    rels[0].delete()
    rev = model.repo.new_revision()
    model.repo.commit_and_remove()

    rels = _homer_to_bart_rels()
    assert len(rels) == 0
    rels = _homer_to_bart_rels(active=False)
    assert len(rels) == 1
    assert rels[0].state == model.State.DELETED

def _test_undelete():
    from ckan import model
    rels = _homer_to_bart_rels(active=False)
    assert len(rels) == 1
    assert rels[0].state != model.State.ACTIVE

    rels[0].state = model.State.ACTIVE
    rev = model.repo.new_revision()
    model.repo.commit_and_remove()

    rels = _homer_to_bart_rels()
    assert len(rels) == 1
    assert rels[0].state == model.State.ACTIVE

    

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

    def test_1_package_count(self):        
        from ckan import model
        pkg_query = model.Session.query(model.Package)
        num_pkgs = pkg_query.count()
        assert num_pkgs == 6, pkg_query.count()

    def test_2_package_details(self):
        _test_family()

    def test_3_delete(self):
        _test_delete()


class Test_1_BasicData(TestMigrationBase):
    @classmethod
    def setup_class(self):
        self.paster('db clean')
        self.setup_db(os.path.join(TEST_DUMPS_PATH, 'test_data_18.pg_dump'))
        # created with:
        # paster db clean && paster db init &&
        # paster create-test-data family
        # export PGPASSWORD=pass&&pg_dump -U tester -D ckantest -h localhost > ../ckan/ckan/migration/tests/test_dumps/test_data_18.pg_dump
        self.paster('db upgrade')

    @classmethod
    def teardown_class(self):
        from ckan import model
        model.Session.close()

    def test_1_package_count(self):        
        from ckan import model
        pkg_query = model.Session.query(model.Package)
        num_pkgs = pkg_query.count()
        assert num_pkgs == 6, pkg_query.all()        

    def test_2_package_details(self):
        _test_family()

    def test_3_undelete(self):
        # migration doesn't give any relationships state,
        # so must make it active
        _test_undelete()
        
    def test_4_delete(self):
        _test_delete()
