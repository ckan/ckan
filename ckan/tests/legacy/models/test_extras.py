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

        pkg._extras[u'country'] = model.PackageExtra(key=u'country', value='us')
        pkg.extras[u'xxx'] = u'yyy'
        pkg.extras[u'format'] = u'rdf'
        model.repo.commit_and_remove()

        # now test it is saved
        rev1 = model.repo.youngest_revision().id
        samepkg = model.Package.by_name(u'warandpeace')
        assert len(samepkg._extras) == 3, samepkg._extras
        assert samepkg.extras[u'country'] == 'us'
        assert samepkg.extras[u'format'] == 'rdf'
        model.Session.remove()

        # now delete and extras
        samepkg = model.Package.by_name(u'warandpeace')
        del samepkg.extras[u'country']
        model.repo.commit_and_remove()

        samepkg = model.Package.by_name(u'warandpeace')
        assert len(samepkg._extras) == 2
        assert len(samepkg.extras) == 2
        extra = model.Session.query(model.PackageExtra).filter_by(key=u'country').first()
        assert not extra, extra
        model.Session.remove()
