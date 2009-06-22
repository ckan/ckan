from ckan.tests import *
import ckan.model as model

class TestRevisionPackages:
    @classmethod
    def setup_class(self):
        model.Session.remove()
        CreateTestData.create()

    @classmethod
    def teardown_class(self):
        CreateTestData.delete()

    def test_1(self):
        rev = model.repo.youngest_revision()
        assert len(rev.packages) == 2
        assert rev.packages[0].__class__.__name__ == 'Package'
        names = [ p.name for p in rev.packages ]
        assert 'annakarenina' in names

