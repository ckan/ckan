# encoding: utf-8

from nose.tools import assert_equal

from ckan import model
from ckan.lib.create_test_data import CreateTestData

from ckan.tests.legacy.functional.api.base import BaseModelApiTestCase


class RevisionsTestCase(BaseModelApiTestCase):

    @classmethod
    def setup_class(cls):
        CreateTestData.create()
        cls.user_name = u'annafan' # created in CreateTestData
        cls.init_extra_environ(cls.user_name)

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()

    def test_register_get_ok(self):
        # Comparison list - newest first
        revs = model.Session.query(model.Revision).\
               order_by(model.Revision.timestamp.desc()).all()
        assert revs

        # Check list of revisions
        offset = self.revision_offset()
        res = self.app.get(offset, status=200)
        revs_result = self.data_from_res(res)

        assert_equal(revs_result, [rev.id for rev in revs])

    def test_entity_get_ok(self):
        rev = model.repo.history().all()[0] # newest revision is the creation of pkgs
        assert rev.id
        assert rev.timestamp.isoformat()
        offset = self.revision_offset(rev.id)
        response = self.app.get(offset, status=[200])
        response_data = self.data_from_res(response)
        assert_equal(rev.id, response_data['id'])
        assert_equal(rev.timestamp.isoformat(), response_data['timestamp'])
        assert 'packages' in response_data
        packages = response_data['packages']
        assert isinstance(packages, list)
        #assert len(packages) != 0, "Revision packages is empty: %s" % packages
        assert self.ref_package(self.anna) in packages, packages
        assert self.ref_package(self.war) in packages, packages

    def test_entity_get_404(self):
        revision_id = "xxxxxxxxxxxxxxxxxxxxxxxxxx"
        offset = self.revision_offset(revision_id)
        res = self.app.get(offset, status=404)
        self.assert_json_response(res, 'Not found')

    def test_entity_get_301(self):
        # see what happens when you miss the ID altogether
        revision_id = ''
        offset = self.revision_offset(revision_id)
        res = self.app.get(offset, status=301)
        # redirects "/api/revision/" to "/api/revision"
