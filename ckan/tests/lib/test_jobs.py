# encoding: utf-8

u'''
Tests for ``ckan.lib.jobs``.
'''

import datetime

from nose.tools import ok_, assert_equal, raises
import rq

import ckan.lib.jobs as jobs
from ckan.tests.helpers import changed_config, recorded_logs, RQTestBase
from ckan.common import config


class TestQueueNamePrefixes(RQTestBase):

    def test_queue_name_prefix_contains_site_id(self):
        prefix = jobs.add_queue_name_prefix(u'')
        ok_(config[u'ckan.site_id'] in prefix)

    def test_queue_name_removal_with_prefix(self):
        plain = u'foobar'
        prefixed = jobs.add_queue_name_prefix(plain)
        assert_equal(jobs.remove_queue_name_prefix(prefixed), plain)

    @raises(ValueError)
    def test_queue_name_removal_without_prefix(self):
        jobs.remove_queue_name_prefix(u'foobar')


class TestEnqueue(RQTestBase):

    def test_enqueue_return_value(self):
        job = self.enqueue()
        ok_(isinstance(job, rq.job.Job))

    def test_enqueue_args(self):
        self.enqueue()
        self.enqueue(args=[1, 2])
        all_jobs = self.all_jobs()
        assert_equal(len(all_jobs), 2)
        assert_equal(len(all_jobs[0].args), 0)
        assert_equal(all_jobs[1].args, [1, 2])

    def test_enqueue_kwargs(self):
        self.enqueue()
        self.enqueue(kwargs={u'foo': 1})
        all_jobs = self.all_jobs()
        assert_equal(len(all_jobs), 2)
        assert_equal(len(all_jobs[0].kwargs), 0)
        assert_equal(all_jobs[1].kwargs, {u'foo': 1})

    def test_enqueue_title(self):
        self.enqueue()
        self.enqueue(title=u'Title')
        all_jobs = self.all_jobs()
        assert_equal(len(all_jobs), 2)
        assert_equal(all_jobs[0].meta[u'title'], None)
        assert_equal(all_jobs[1].meta[u'title'], u'Title')

    def test_enqueue_queue(self):
        self.enqueue()
        self.enqueue(queue=u'my_queue')
        all_jobs = self.all_jobs()
        assert_equal(len(all_jobs), 2)
        assert_equal(all_jobs[0].origin,
                     jobs.add_queue_name_prefix(jobs.DEFAULT_QUEUE_NAME))
        assert_equal(all_jobs[1].origin,
                     jobs.add_queue_name_prefix(u'my_queue'))


class TestGetAllQueues(RQTestBase):

    def test_foreign_queues_are_ignored(self):
        u'''
        Test that foreign RQ-queues are ignored.
        '''
        # Create queues for this CKAN instance
        self.enqueue(queue=u'q1')
        self.enqueue(queue=u'q2')
        # Create queue for another CKAN instance
        with changed_config(u'ckan.site_id', u'some-other-ckan-instance'):
            self.enqueue(queue=u'q2')
        # Create queue not related to CKAN
        rq.Queue(u'q4').enqueue_call(jobs.test_job)
        all_queues = jobs.get_all_queues()
        names = {jobs.remove_queue_name_prefix(q.name) for q in all_queues}
        assert_equal(names, {u'q1', u'q2'})


class TestGetQueue(RQTestBase):

    def test_get_queue_default_queue(self):
        u'''
        Test that the default queue is returned if no queue is given.
        '''
        q = jobs.get_queue()
        assert_equal(jobs.remove_queue_name_prefix(q.name),
                     jobs.DEFAULT_QUEUE_NAME)

    def test_get_queue_other_queue(self):
        u'''
        Test that a different queue can be given.
        '''
        q = jobs.get_queue(u'my_queue')
        assert_equal(jobs.remove_queue_name_prefix(q.name), u'my_queue')


class TestJobFromID(RQTestBase):

    def test_job_from_id_existing(self):
        job = self.enqueue()
        assert_equal(jobs.job_from_id(job.id), job)
        job = self.enqueue(queue=u'my_queue')
        assert_equal(jobs.job_from_id(job.id), job)

    @raises(KeyError)
    def test_job_from_id_not_existing(self):
        jobs.job_from_id(u'does-not-exist')


class TestDictizeJob(RQTestBase):

    def test_dictize_job(self):
        job = self.enqueue(title=u'Title', queue=u'my_queue')
        d = jobs.dictize_job(job)
        assert_equal(d[u'id'], job.id)
        assert_equal(d[u'title'], u'Title')
        assert_equal(d[u'queue'], u'my_queue')
        dt = datetime.datetime.strptime(d[u'created'], u'%Y-%m-%dT%H:%M:%S')
        now = datetime.datetime.utcnow()
        ok_(abs((now - dt).total_seconds()) < 10)


def failing_job():
    u'''
    A background job that fails.
    '''
    raise RuntimeError(u'JOB FAILURE')


class TestWorker(RQTestBase):

    def test_worker_logging_lifecycle(self):
        u'''
        Test that a logger's lifecycle is logged.
        '''
        queue = u'my_queue'
        job = self.enqueue(queue=queue)
        with recorded_logs(u'ckan.lib.jobs') as logs:
            worker = jobs.Worker([queue])
            worker.work(burst=True)
        messages = logs.messages[u'info']
        # We expect 4 log messages: Worker start, job start, job end,
        # worker end.
        assert_equal(len(messages), 4)
        ok_(worker.key in messages[0])
        ok_(queue in messages[0])
        ok_(worker.key in messages[1])
        ok_(job.id in messages[1])
        ok_(worker.key in messages[2])
        ok_(job.id in messages[2])
        ok_(worker.key in messages[3])

    def test_worker_exception_logging(self):
        u'''
        Test that exceptions in a job are logged.
        '''
        job = self.enqueue(failing_job)
        worker = jobs.Worker()

        # Prevent worker from forking so that we can capture log
        # messages from within the job
        def execute_job(*args, **kwargs):
            return worker.perform_job(*args, **kwargs)

        worker.execute_job = execute_job
        with recorded_logs(u'ckan.lib.jobs') as logs:
            worker.work(burst=True)
        logs.assert_log(u'error', u'JOB FAILURE')

    def test_worker_default_queue(self):
        self.enqueue()
        self.enqueue(queue=u'my_queue')
        jobs.Worker().work(burst=True)
        all_jobs = self.all_jobs()
        assert_equal(len(all_jobs), 1)
        assert_equal(jobs.remove_queue_name_prefix(all_jobs[0].origin),
                     u'my_queue')

    def test_worker_multiple_queues(self):
        self.enqueue()
        self.enqueue(queue=u'queue1')
        self.enqueue(queue=u'queue2')
        jobs.Worker([u'queue1', u'queue2']).work(burst=True)
        all_jobs = self.all_jobs()
        assert_equal(len(all_jobs), 1)
        assert_equal(jobs.remove_queue_name_prefix(all_jobs[0].origin),
                     jobs.DEFAULT_QUEUE_NAME)
