# encoding: utf-8

import datetime

from nose.tools import assert_equal

from ckan.tests.legacy import *
import ckan.model as model

# NB Lots of revision tests are part of vdm. No need to repeat those here.

class TestRevision:
    @classmethod
    def setup_class(cls):
        # Create a test package
        rev = model.repo.new_revision()
        rev.author = 'Tester'
        rev.timestamp = datetime.datetime(2020, 1, 1)
        rev.approved_timestamp = datetime.datetime(2020, 1, 2)
        rev.message = 'Test message'
        pkg = model.Package(name='testpkg')
        model.Session.add(pkg)
        model.Session.commit()
        model.Session.remove()

        revs = model.Session.query(model.Revision).\
               order_by(model.Revision.timestamp.desc()).all()
        cls.rev = revs[0] # newest

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()

    def test_revision_as_dict(self):
        rev_dict = model.revision_as_dict(self.rev,
                                          include_packages=True,
                                          include_groups=True,
                                          ref_package_by='name')
        
        assert_equal(rev_dict['id'], self.rev.id)
        assert_equal(rev_dict['author'], self.rev.author)
        assert_equal(rev_dict['timestamp'], '2020-01-01T00:00:00')
        assert_equal(rev_dict['approved_timestamp'], '2020-01-02T00:00:00')
        assert_equal(rev_dict['message'], self.rev.message)
        assert_equal(rev_dict['packages'], [u'testpkg'])
        
