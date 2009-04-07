# needed for config to be set and db access to work
from ckan.tests import *
import ckan.model as model

class TestExtras:
    @classmethod 
    def setup_class(self):
        CreateTestData.create()

    @classmethod 
    def teardown_class(self):
        CreateTestData.delete()

    def test_1(self):
        pkg = model.Package.by_name(CreateTestData.pkgname1)
        assert pkg is not None
        pkg._extras['country'] = model.Extra(key='country', value='us')
        pkg.extras['format'] = 'rdf'
        # save and clear
        model.repo.commit_and_remove()
        # now test it is saved
        samepkg = model.Package.by_name(CreateTestData.pkgname1)
        print samepkg._extras
        assert len(samepkg._extras) == 2
        assert samepkg.extras['country'] == 'us'
        assert samepkg.extras['format'] == 'rdf'

