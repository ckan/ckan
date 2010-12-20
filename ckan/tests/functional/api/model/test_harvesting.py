from ckan.tests.functional.api.base import BaseModelApiTestCase
from ckan.tests.functional.api.base import Api1TestCase as Version1TestCase 
from ckan.tests.functional.api.base import Api2TestCase as Version2TestCase 
from ckan.tests.functional.api.base import ApiUnversionedTestCase as UnversionedTestCase 

# Todo: Remove this ckan.model stuff.
import ckan.model as model

class HarvestingTestCase(BaseModelApiTestCase):

    commit_changesets = False
    reuse_common_fixtures = True

    def setup(self):
        model.repo.rebuild_db()
        super(HarvestingTestCase, self).setup()
        self.source = None
        self.source1 = None
        self.source2 = None
        self.source3 = None
        self.source4 = None
        self.source5 = None
        self.job = None
        self.job1 = None
        self.job2 = None
        self.job3 = None

    def teardown(self):
        if self.job:
            self.delete_commit(self.job)
        if self.job1:
            self.delete_commit(self.job1)
        if self.job2:
            self.delete_commit(self.job2)
        if self.job3:
            self.delete_commit(self.job3)
        if self.source:
            self.delete_commit(self.source)
        if self.source1:
            self.delete_commit(self.source1)
        if self.source2:
            self.delete_commit(self.source2)
        if self.source3:
            self.delete_commit(self.source3)
        if self.source4:
            self.delete_commit(self.source4)
        if self.source5:
            self.delete_commit(self.source5)
        super(HarvestingTestCase, self).teardown()

    def _create_harvest_source_fixture(self, **kwds):
        source = model.HarvestSource(**kwds)
        model.Session.add(source)
        model.Session.commit()
        assert source.id
        return source

    def _create_harvesting_job_fixture(self, **kwds):
        if not kwds.get('user_ref'):
            kwds['user_ref'] = u'c_publisher_user'
        job = model.HarvestingJob(**kwds)
        model.Session.add(job)
        model.Session.commit()
        assert job.id
        return job

    def test_harvestsource_entity_get_ok(self):
        # Setup harvest source fixture.
        fixture_url = u'http://localhost/'
        self.source = self._create_harvest_source_fixture(url=fixture_url)
        offset = self.offset('/rest/harvestsource/%s' % self.source.id)
        res = self.app.get(offset, status=[200])
        source_data = self.data_from_res(res)
        assert 'url' in source_data, "No 'id' in changeset data: %s" % source_data
        self.assert_equal(source_data.get('url'), fixture_url)

    def test_harvestsource_entity_get_not_found(self):
        offset = self.offset('/rest/harvestsource/%s' % "notasource")
        self.app.get(offset, status=[404])

    def test_publisher_harvestsource_register_get_ok(self):
        # Setup harvest source fixtures.
        fixture_url = u'http://localhost/'
        self.source1 = self._create_harvest_source_fixture(url=fixture_url+'1', publisher_ref=u'pub1')
        self.source2 = self._create_harvest_source_fixture(url=fixture_url+'2', publisher_ref=u'pub1')
        self.source3 = self._create_harvest_source_fixture(url=fixture_url+'3', publisher_ref=u'pub1')
        self.source4 = self._create_harvest_source_fixture(url=fixture_url+'4', publisher_ref=u'pub2')
        self.source5 = self._create_harvest_source_fixture(url=fixture_url+'5', publisher_ref=u'pub2')
        offset = self.offset('/rest/harvestsource/publisher/pub1')
        res = self.app.get(offset, status=[200])
        source_data = self.data_from_res(res)
        self.assert_equal(len(source_data), 3)
        offset = self.offset('/rest/harvestsource/publisher/pub2')
        res = self.app.get(offset, status=[200])
        source_data = self.data_from_res(res)
        self.assert_equal(len(source_data), 2)
        
    def test_harvestingjob_entity_get_ok(self):
        # Setup harvesting job fixture.
        fixture_url = u'http://localhost/6'
        self.source = self._create_harvest_source_fixture(url=fixture_url)
        self.job = self._create_harvesting_job_fixture(source_id=self.source.id)
        offset = self.offset('/rest/harvestingjob/%s' % self.job.id)
        res = self.app.get(offset, status=[200])
        job_data = self.data_from_res(res)
        self.assert_equal(job_data.get('source_id'), self.source.id)

    def test_harvestingjob_entity_get_not_found(self):
        # Setup harvesting job fixture.
        offset = self.offset('/rest/harvestingjob/%s' % "notajob")
        self.app.get(offset, status=[404])

    def test_harvestingjob_register_post_ok(self):
        # Setup harvest source fixture.
        fixture_url = u'http://localhost/7'
        self.source = self._create_harvest_source_fixture(url=fixture_url)
        # Prepare and send POST request to register.
        offset = self.offset('/rest/harvestingjob')
        #  - invalid example.
        job_details = {
            'source_id': 'made-up-source-id',
            'user_ref': u'a_publisher_user',
        }
        assert not model.HarvestingJob.get(u'a_publisher_user', default=None, attr='user_ref')
        response = self.post(offset, job_details, status=400)
        job_error = self.data_from_res(response)
        assert "does not exist" in job_error
        assert not model.HarvestingJob.get(u'a_publisher_user', default=None, attr='user_ref')
        #  - invalid example.
        job_details = {
            'source_id': self.source.id,
            'user_ref': u'',
        }
        assert not model.HarvestingJob.get(u'a_publisher_user', None, 'user_ref')
        response = self.post(offset, job_details, status=400)
        job_error = self.data_from_res(response)
        assert "You must supply a user_ref" in job_error
        assert not model.HarvestingJob.get(self.source.id, default=None, attr='source_id')
        #  - valid example.
        job_details = {
            'source_id': self.source.id,
            'user_ref': u'a_publisher_user',
        }
        assert not model.HarvestingJob.get(u'a_publisher_user', None, 'user_ref')
        response = self.post(offset, job_details)
        new_job = self.data_from_res(response)
        assert new_job['id']
        self.assert_equal(new_job['source_id'], self.source.id)
        self.assert_equal(new_job['user_ref'], u'a_publisher_user')
        self.job = model.HarvestingJob.get(self.source.id, attr='source_id')
        model.HarvestingJob.get(u'a_publisher_user', attr='user_ref')

    def test_harvestingjob_register_get_filter_by_status(self):
        # Setup harvest source fixture.
        fixture_url = u'http://localhost/8'
        self.source = self._create_harvest_source_fixture(url=fixture_url)
        self.job = self._create_harvesting_job_fixture(source_id=self.source.id)
        register_offset = self.offset('/rest/harvestingjob')
        self.assert_equal(self.job.status, 'New')
 
        filter_offset = '/status/new'
        offset = register_offset + filter_offset
        res = self.get(offset)
        data = self.data_from_res(res)
        self.assert_equal(data, [self.job.id])

        filter_offset = '/status/error'
        offset = register_offset + filter_offset
        res = self.get(offset)
        data = self.data_from_res(res)
        self.assert_equal(data, [])

        self.job.status = u'Error'
        self.job.save()
        res = self.get(offset)
        data = self.data_from_res(res)
        self.assert_equal(data, [self.job.id])

        filter_offset = '/status/new'
        offset = register_offset + filter_offset
        res = self.get(offset)
        data = self.data_from_res(res)
        self.assert_equal(data, [])

        filter_offset = '/status/error'
        offset = register_offset + filter_offset
        res = self.get(offset)
        data = self.data_from_res(res)
        self.assert_equal(data, [self.job.id])

    def test_harvestingjob_entity_delete_ok(self):
        # Setup harvesting job fixture.
        fixture_url = u'http://localhost/6'
        self.source = self._create_harvest_source_fixture(url=fixture_url)
        self.job = self._create_harvesting_job_fixture(source_id=self.source.id)
        offset = self.offset('/rest/harvestingjob/%s' % self.job.id)
        self.get(offset, status=[200])
        res = self.app_delete(offset, status=[200])
        self.get(offset, status=[404])

    def test_harvestingjob_entity_delete_denied(self):
        self.send_authorization_header = False
        # Setup harvesting job fixture.
        fixture_url = u'http://localhost/6'
        self.source = self._create_harvest_source_fixture(url=fixture_url)
        self.job = self._create_harvesting_job_fixture(source_id=self.source.id)
        offset = self.offset('/rest/harvestingjob/%s' % self.job.id)
        self.get(offset, status=[200])
        self.app_delete(offset, status=[403])

    def test_harvestingjob_entity_delete_not_found(self):
        # Setup harvesting job fixture.
        offset = self.offset('/rest/harvestingjob/%s' % "notajob")
        self.get(offset, status=[404])

class TestHarvestingVersion1(Version1TestCase, HarvestingTestCase): pass
class TestHarvestingVersion2(Version2TestCase, HarvestingTestCase): pass
class TestHarvestingUnversioned(UnversionedTestCase, HarvestingTestCase): pass

