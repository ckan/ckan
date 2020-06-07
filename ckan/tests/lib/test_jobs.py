# encoding: utf-8

u"""
Tests for ``ckan.lib.jobs``.
"""

import datetime

import pytest
import rq

import ckan.lib.jobs as jobs
from ckan.common import config
from ckan.logic import NotFound
from ckan import model

from ckan.tests.helpers import (
    call_action,
    changed_config,
    recorded_logs,
    RQTestBase,
)


class TestQueueNamePrefixes(RQTestBase):
    def test_queue_name_prefix_contains_site_id(self):
        prefix = jobs.add_queue_name_prefix(u"")
        assert config[u"ckan.site_id"] in prefix

    def test_queue_name_removal_with_prefix(self):
        plain = u"foobar"
        prefixed = jobs.add_queue_name_prefix(plain)
        assert jobs.remove_queue_name_prefix(prefixed) == plain

    def test_queue_name_removal_without_prefix(self):
        with pytest.raises(ValueError):
            jobs.remove_queue_name_prefix(u"foobar")


class TestEnqueue(RQTestBase):
    def test_enqueue_return_value(self):
        job = self.enqueue()
        assert isinstance(job, rq.job.Job)

    def test_enqueue_args(self):
        self.enqueue()
        self.enqueue(args=[1, 2])
        all_jobs = self.all_jobs()
        assert len(all_jobs) == 2
        assert len(all_jobs[0].args) == 0
        assert all_jobs[1].args == [1, 2]

    def test_enqueue_kwargs(self):
        self.enqueue()
        self.enqueue(kwargs={u"foo": 1})
        all_jobs = self.all_jobs()
        assert len(all_jobs) == 2
        assert len(all_jobs[0].kwargs) == 0
        assert all_jobs[1].kwargs == {u"foo": 1}

    def test_enqueue_title(self):
        self.enqueue()
        self.enqueue(title=u"Title")
        all_jobs = self.all_jobs()
        assert len(all_jobs) == 2
        assert all_jobs[0].meta[u"title"] is None
        assert all_jobs[1].meta[u"title"] == u"Title"

    def test_enqueue_queue(self):
        self.enqueue()
        self.enqueue(queue=u"my_queue")
        all_jobs = self.all_jobs()
        assert len(all_jobs) == 2
        assert sorted(job.origin for job in all_jobs) == sorted([
            jobs.add_queue_name_prefix(jobs.DEFAULT_QUEUE_NAME),
            jobs.add_queue_name_prefix(u"my_queue")
        ])

    def test_enqueue_timeout(self):
        self.enqueue()
        self.enqueue(rq_kwargs={u'timeout': 0})
        self.enqueue(rq_kwargs={u'timeout': -1})
        self.enqueue(rq_kwargs={u'timeout': 3600})
        all_jobs = self.all_jobs()
        assert len(all_jobs) == 4
        assert all_jobs[0].timeout == 180
        assert all_jobs[1].timeout == 180
        assert all_jobs[2].timeout == -1
        assert all_jobs[3].timeout == 3600


class TestGetAllQueues(RQTestBase):
    def test_foreign_queues_are_ignored(self):
        u"""
        Test that foreign RQ-queues are ignored.
        """
        # Create queues for this CKAN instance
        self.enqueue(queue=u"q1")
        self.enqueue(queue=u"q2")
        # Create queue for another CKAN instance
        with changed_config(u"ckan.site_id", u"some-other-ckan-instance"):
            self.enqueue(queue=u"q2")
        # Create queue not related to CKAN
        rq.Queue(u"q4").enqueue_call(jobs.test_job)
        all_queues = jobs.get_all_queues()
        names = {jobs.remove_queue_name_prefix(q.name) for q in all_queues}
        assert names == {u"q1", u"q2"}


class TestGetQueue(RQTestBase):
    def test_get_queue_default_queue(self):
        u"""
        Test that the default queue is returned if no queue is given.
        """
        q = jobs.get_queue()
        assert jobs.remove_queue_name_prefix(q.name) == jobs.DEFAULT_QUEUE_NAME

    def test_get_queue_other_queue(self):
        u"""
        Test that a different queue can be given.
        """
        q = jobs.get_queue(u"my_queue")
        assert jobs.remove_queue_name_prefix(q.name) == u"my_queue"


class TestJobFromID(RQTestBase):
    def test_job_from_id_existing(self):
        job = self.enqueue()
        assert jobs.job_from_id(job.id) == job
        job = self.enqueue(queue=u"my_queue")
        assert jobs.job_from_id(job.id) == job

    def test_job_from_id_not_existing(self):
        with pytest.raises(KeyError):
            jobs.job_from_id(u"does-not-exist")


class TestDictizeJob(RQTestBase):
    def test_dictize_job(self):
        job = self.enqueue(title=u"Title", queue=u"my_queue")
        d = jobs.dictize_job(job)
        assert d[u"id"] == job.id
        assert d[u"title"] == u"Title"
        assert d[u"queue"] == u"my_queue"
        dt = datetime.datetime.strptime(d[u"created"], u"%Y-%m-%dT%H:%M:%S")
        now = datetime.datetime.utcnow()
        assert abs((now - dt).total_seconds()) < 10


def failing_job():
    u"""
    A background job that fails.
    """
    raise RuntimeError(u"JOB FAILURE")


def database_job(pkg_id, pkg_title):
    u"""
    A background job that uses the PostgreSQL database.

    Appends ``pkg_title`` to the title of package ``pkg_id``.
    """
    pkg_dict = call_action(u"package_show", id=pkg_id)
    pkg_dict[u"title"] += pkg_title
    pkg_dict = call_action(u"package_update", **pkg_dict)


class TestWorker(RQTestBase):
    def test_worker_logging_lifecycle(self):
        u"""
        Test that a logger's lifecycle is logged.
        """
        queue = u"my_queue"
        job = self.enqueue(queue=queue)
        with recorded_logs(u"ckan.lib.jobs") as logs:
            worker = jobs.Worker([queue])
            worker.work(burst=True)
        messages = logs.messages[u"info"]
        # We expect 4 log messages: Worker start, job start, job end,
        # worker end.
        assert len(messages) == 4
        assert worker.key in messages[0]
        assert queue in messages[0]
        assert worker.key in messages[1]
        assert job.id in messages[1]
        assert worker.key in messages[2]
        assert job.id in messages[2]
        assert worker.key in messages[3]

    def test_worker_exception_logging(self):
        u"""
        Test that exceptions in a job are logged.
        """
        job = self.enqueue(failing_job)
        worker = jobs.Worker()

        # Prevent worker from forking so that we can capture log
        # messages from within the job
        def execute_job(*args, **kwargs):
            return worker.perform_job(*args, **kwargs)

        worker.execute_job = execute_job
        with recorded_logs(u"ckan.lib.jobs") as logs:
            worker.work(burst=True)
        logs.assert_log(u"error", u"JOB FAILURE")

    def test_worker_default_queue(self):
        self.enqueue()
        self.enqueue(queue=u"my_queue")
        jobs.Worker().work(burst=True)
        all_jobs = self.all_jobs()
        assert len(all_jobs) == 1
        assert jobs.remove_queue_name_prefix(all_jobs[0].origin) == u"my_queue"

    def test_worker_multiple_queues(self):
        self.enqueue()
        self.enqueue(queue=u"queue1")
        self.enqueue(queue=u"queue2")
        jobs.Worker([u"queue1", u"queue2"]).work(burst=True)
        all_jobs = self.all_jobs()
        assert len(all_jobs) == 1
        assert (
            jobs.remove_queue_name_prefix(all_jobs[0].origin)
            == jobs.DEFAULT_QUEUE_NAME
        )

    def test_worker_database_access(self):
        u"""
        Test database access from within the worker.
        """
        # See https://github.com/ckan/ckan/issues/3243
        pkg_name = u"test-worker-database-access"
        try:
            pkg_dict = call_action(u"package_show", id=pkg_name)
        except NotFound:
            pkg_dict = call_action(u"package_create", name=pkg_name)
        pkg_dict[u"title"] = u"foo"
        pkg_dict = call_action(u"package_update", **pkg_dict)
        titles = u"1 2 3".split()
        for title in titles:
            self.enqueue(database_job, args=[pkg_dict[u"id"], title])
        jobs.Worker().work(burst=True)
        # Aside from ensuring that the jobs succeeded, this also checks
        # that database access still works in the main process.
        pkg_dict = call_action(u"package_show", id=pkg_name)
        assert pkg_dict[u"title"] == u"foo" + u"".join(titles)

    def test_fork_within_a_transaction(self):
        u"""
        Test forking a worker horse within a database transaction.

        The original instances should be unchanged but their session
        must be closed.
        """
        pkg_name = u"test-fork-within-a-transaction"
        pkg = model.Package.get(pkg_name)
        if not pkg:
            pkg = model.Package(name=pkg_name)
        pkg.title = u"foo"
        pkg.save()
        pkg.title = u"bar"
        self.enqueue(database_job, [pkg.id, u"foo"])
        jobs.Worker().work(burst=True)
        assert pkg.title == u"bar"  # Original instance is unchanged
        # The original session has been closed, `pkg.Session` uses the new
        # session in which `pkg` is not registered.
        assert pkg not in pkg.Session
        pkg = model.Package.get(pkg.id)  # Get instance from new session
        assert pkg.title == u"foofoo"  # Worker only saw committed changes
