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
        startrev = model.repo.youngest_revision().id
        pkg = model.Package.by_name(CreateTestData.pkgname2)
        assert pkg is not None

        rev = model.repo.new_revision()
        pkg._extras[u'country'] = model.PackageExtra(key=u'country', value='us')
        pkg.extras_active[u'xxx'] = model.PackageExtra(key=u'xxx', value='yyy')
        pkg.extras[u'format'] = 'rdf'
        # save and clear
        model.repo.commit_and_remove()

        # now test it is saved
        rev1 = model.repo.youngest_revision().id
        assert rev1 == startrev + 1
        samepkg = model.Package.by_name(CreateTestData.pkgname2)
        assert len(samepkg._extras) == 3, samepkg._extras
        assert samepkg.extras_active[u'country'].value == 'us', samepkg.extras_active
        assert samepkg.extras[u'country'] == 'us'
        assert samepkg.extras[u'format'] == 'rdf'
        model.Session.remove()

        # now delete and extras
        samepkg = model.Package.by_name(CreateTestData.pkgname2)
        model.repo.new_revision()
        del samepkg.extras[u'country']
        model.repo.commit_and_remove()

        samepkg = model.Package.by_name(CreateTestData.pkgname2)
        assert len(samepkg._extras) == 3
        assert len(samepkg.extras) == 2
        extra = model.PackageExtra.query.filter_by(key=u'country').first()
        assert extra and extra.state.name == 'deleted', extra
        
        samepkg.get_as_of(model.Revision.query.get(rev1))
        assert len(samepkg.extras) == 3
        model.Session.remove()

        # now restore it ...
        model.repo.new_revision()
        samepkg = model.Package.by_name(CreateTestData.pkgname2)
        samepkg.extras[u'country'] = 'uk'
        model.repo.commit_and_remove()

        samepkg = model.Package.by_name(CreateTestData.pkgname2)
        assert len(samepkg.extras) == 3
        assert len(samepkg._extras) == 3
        assert samepkg.extras[u'country'] == 'uk'
        
