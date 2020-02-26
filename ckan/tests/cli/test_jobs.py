# -*- coding: utf-8 -*-

import datetime
import tempfile

import ckan.lib.jobs as jobs
from ckan.cli.cli import ckan
from ckan.tests.helpers import RQTestBase


class TestJobShow(RQTestBase):
    def test_list_default_queue(self, cli):
        """
        Test output of ``jobs list`` for default queue.
        """
        job = self.enqueue()
        result = cli.invoke(ckan, [u"jobs", u"list"])
        fields = result.output.split()
        assert len(fields) == 3
        dt = datetime.datetime.strptime(fields[0], u"%Y-%m-%dT%H:%M:%S")
        now = datetime.datetime.utcnow()
        assert abs((now - dt).total_seconds()) < 10
        assert fields[1] == job.id
        assert fields[2] == jobs.DEFAULT_QUEUE_NAME

    def test_list_other_queue(self, cli):
        """
        Test output of ``jobs.list`` for non-default queue.
        """
        job = self.enqueue(queue=u"my_queue")
        result = cli.invoke(ckan, [u"jobs", u"list"])
        fields = result.output.split()
        assert len(fields) == 3
        assert fields[2] == u"my_queue"

    def test_list_title(self, cli):
        """
        Test title output of ``jobs list``.
        """
        job = self.enqueue(title=u"My_Title")
        result = cli.invoke(ckan, [u"jobs", u"list"])
        fields = result.output.split()
        assert len(fields) == 4
        assert fields[3] == u'"My_Title"'

    def test_list_filter(self, cli):
        """
        Test filtering by queues for ``jobs list``.
        """
        job1 = self.enqueue(queue=u"q1")
        job2 = self.enqueue(queue=u"q2")
        job3 = self.enqueue(queue=u"q3")
        result = cli.invoke(ckan, [u"jobs", u"list", u"q1", u"q2"])
        assert u"q1" in result.output
        assert u"q2" in result.output
        assert u"q3" not in result.output


class TestJobShow(RQTestBase):
    """
    Tests for ``paster jobs show``.
    """

    def test_show_existing(self, cli):
        """
        Test ``jobs show`` for an existing job.
        """
        job = self.enqueue(queue=u"my_queue", title=u"My Title")
        result = cli.invoke(ckan, [u"jobs", u"show", job.id])
        assert job.id in result.output
        assert jobs.remove_queue_name_prefix(job.origin) in result.output

    def test_show_missing_id(self, cli):
        """
        Test ``jobs show`` with a missing ID.
        """
        result = cli.invoke(ckan, [u"jobs", u"show"])
        assert result.exit_code


class TestJobsCancel(RQTestBase):
    """
    Tests for ``paster jobs cancel``.
    """

    def test_cancel_existing(self, cli):
        """
        Test ``jobs cancel`` for an existing job.
        """
        job1 = self.enqueue()
        job2 = self.enqueue()
        result = cli.invoke(ckan, [u"jobs", u"cancel", job1.id])
        all_jobs = self.all_jobs()
        assert len(all_jobs) == 1
        assert all_jobs[0].id == job2.id
        assert job1.id in result.output

    def test_cancel_not_existing(self, cli):
        """
        Test ``jobs cancel`` for a not existing job.
        """
        result = cli.invoke(ckan, [u"jobs", u"cancel", u"does-not-exist"])
        assert result.exit_code
        assert u"does-not-exist" in result.output

    def test_cancel_missing_id(self, cli):
        """
        Test ``jobs cancel`` with a missing ID.
        """
        result = cli.invoke(ckan, [u"jobs", u"cancel"])
        assert result.exit_code


class TestJobsClear(RQTestBase):
    """
    Tests for ``paster jobs clear``.
    """

    def test_clear_all_queues(self, cli):
        """
        Test clearing all queues via ``jobs clear``.
        """
        self.enqueue()
        self.enqueue()
        self.enqueue(queue=u"q1")
        self.enqueue(queue=u"q2")
        result = cli.invoke(ckan, [u"jobs", u"clear"])
        assert jobs.DEFAULT_QUEUE_NAME in result.output
        assert u"q1" in result.output
        assert u"q2" in result.output
        assert self.all_jobs() == []

    def test_clear_specific_queues(self, cli):
        """
        Test clearing specific queues via ``jobs clear``.
        """
        job1 = self.enqueue()
        job2 = self.enqueue(queue=u"q1")
        self.enqueue(queue=u"q2")
        self.enqueue(queue=u"q2")
        self.enqueue(queue=u"q3")
        result = cli.invoke(ckan, [u"jobs", u"clear", u"q2", u"q3"])
        assert u"q2" in result.output
        assert u"q3" in result.output
        assert jobs.DEFAULT_QUEUE_NAME not in result.output
        assert u"q1" not in result.output
        all_jobs = self.all_jobs()
        assert set(all_jobs) == {job1, job2}


class TestJobsTest(RQTestBase):
    """
    Tests for ``paster jobs test``.
    """

    def test_test_default_queue(self, cli):
        """
        Test ``jobs test`` for the default queue.
        """
        cli.invoke(ckan, [u"jobs", u"test"])
        all_jobs = self.all_jobs()
        assert len(all_jobs) == 1
        assert (
            jobs.remove_queue_name_prefix(all_jobs[0].origin)
            == jobs.DEFAULT_QUEUE_NAME
        )

    def test_test_specific_queues(self, cli):
        """
        Test ``jobs test`` for specific queues.
        """

        cli.invoke(ckan, [u"jobs", u"test", u"q1", u"q2"])
        all_jobs = self.all_jobs()
        assert len(all_jobs) == 2
        assert {jobs.remove_queue_name_prefix(j.origin) for j in all_jobs} == {
            u"q1",
            u"q2",
        }


class TestJobsWorker(RQTestBase):
    """
    Tests for ``paster jobs worker``.
    """

    # All tests of ``jobs worker`` must use the ``--burst`` option to
    # make sure that the worker exits.

    def test_worker_default_queue(self, cli):
        """
        Test ``jobs worker`` with the default queue.
        """
        with tempfile.NamedTemporaryFile(delete=False) as f:
            self.enqueue(os.remove, args=[f.name])
            cli.invoke(ckan, [u"jobs", u"worker", u"--burst"])
            all_jobs = self.all_jobs()
            assert all_jobs == []
            assert not (os.path.isfile(f.name))

    def test_worker_specific_queues(self, cli):
        """
        Test ``jobs worker`` with specific queues.
        """
        with tempfile.NamedTemporaryFile(delete=False) as f:
            with tempfile.NamedTemporaryFile(delete=False) as g:
                job1 = self.enqueue()
                job2 = self.enqueue(queue=u"q2")
                self.enqueue(os.remove, args=[f.name], queue=u"q3")
                self.enqueue(os.remove, args=[g.name], queue=u"q4")
                cli.invoke(ckan, [u"jobs", u"worker", u"--burst", u"q3", u"q4"])
                all_jobs = self.all_jobs()
                assert set(all_jobs) == {job1, job2}
                assert not (os.path.isfile(f.name))
                assert not (os.path.isfile(g.name))
