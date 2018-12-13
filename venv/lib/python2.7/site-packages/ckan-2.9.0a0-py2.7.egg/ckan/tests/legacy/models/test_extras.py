# encoding: utf-8

from ckan.tests.legacy import *

import ckan.model as model

class TestExtras:
    @classmethod 
    def setup_class(self):
        CreateTestData.create()

    @classmethod 
    def teardown_class(self):
        model.repo.rebuild_db()

    def test_1(self):
        startrev = model.repo.youngest_revision().id
        pkg = model.Package.by_name(u'warandpeace')
        assert pkg is not None

        rev = model.repo.new_revision()
        pkg._extras[u'country'] = model.PackageExtra(key=u'country', value='us')
        pkg.extras_active[u'xxx'] = model.PackageExtra(key=u'xxx', value='yyy')
        pkg.extras[u'format'] = u'rdf'
        model.repo.commit_and_remove()

        # now test it is saved
        rev1 = model.repo.youngest_revision().id
        samepkg = model.Package.by_name(u'warandpeace')
        assert len(samepkg._extras) == 3, samepkg._extras
        assert samepkg.extras_active[u'country'].value == 'us', samepkg.extras_active
        assert samepkg.extras[u'country'] == 'us'
        assert samepkg.extras[u'format'] == 'rdf'
        model.Session.remove()

        # now delete and extras
        samepkg = model.Package.by_name(u'warandpeace')
        model.repo.new_revision()
        del samepkg.extras[u'country']
        model.repo.commit_and_remove()

        samepkg = model.Package.by_name(u'warandpeace')
        assert len(samepkg._extras) == 3
        assert len(samepkg.extras) == 2
        extra = model.Session.query(model.PackageExtra).filter_by(key=u'country').first()
        assert extra and extra.state == model.State.DELETED, extra
        model.Session.remove()
        
        samepkg = model.Package.by_name(u'warandpeace')
        samepkg.get_as_of(model.Session.query(model.Revision).get(rev1))
        assert len(samepkg.extras) == 3, len(samepkg.extras)
        model.Session.remove()

        # now restore it ...
        model.repo.new_revision()
        samepkg = model.Package.by_name(u'warandpeace')
        samepkg.extras[u'country'] = 'uk'
        model.repo.commit_and_remove()

        samepkg = model.Package.by_name(u'warandpeace')
        assert len(samepkg.extras) == 3
        assert len(samepkg._extras) == 3
        assert samepkg.extras[u'country'] == 'uk'
        
