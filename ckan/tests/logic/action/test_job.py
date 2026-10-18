"""Tests for actions and authorization in ckan/logic/action/job.py."""

import datetime
import re

import pytest

import ckan.lib.jobs as jobs
import ckan.logic as logic
import ckan.tests.helpers as helpers


class TestJobClear(helpers.FunctionalRQTestBase):
    def test_all_queues(self):
        """
        Test clearing all queues.
        """
        self.enqueue()
        self.enqueue(queue="q")
        self.enqueue(queue="q")
        self.enqueue(queue="q")
        queues = helpers.call_action("job_clear")
        assert {jobs.DEFAULT_QUEUE_NAME, "q"} == set(queues)
        all_jobs = self.all_jobs()
        assert len(all_jobs) == 0

    def test_specific_queues(self):
        """
        Test clearing specific queues.
        """
        job1 = self.enqueue()
        self.enqueue(queue="q1")
        self.enqueue(queue="q1")
        self.enqueue(queue="q2")
        with helpers.recorded_logs("ckan.logic") as logs:
            queues = helpers.call_action("job_clear", queues=["q1", "q2"])
        assert {"q1", "q2"} == set(queues)
        all_jobs = self.all_jobs()
        assert len(all_jobs) == 1
        assert all_jobs[0] == job1
        logs.assert_log("info", "q1")
        logs.assert_log("info", "q2")


class TestJobCancel(helpers.FunctionalRQTestBase):
    def test_existing_job(self):
        """
        Test cancelling an existing job.
        """
        job1 = self.enqueue(queue="q")
        job2 = self.enqueue(queue="q")
        with helpers.recorded_logs("ckan.logic") as logs:
            helpers.call_action("job_cancel", id=job1.id)
        all_jobs = self.all_jobs()
        assert len(all_jobs) == 1
        assert all_jobs[0] == job2
        with pytest.raises(KeyError):
            jobs.job_from_id(job1.id)
        logs.assert_log("info", re.escape(job1.id))

    def test_not_existing_job(self):
        with pytest.raises(logic.NotFound):
            helpers.call_action("job_cancel", id="does-not-exist")


class TestJobList(helpers.FunctionalRQTestBase):
    def test_all_queues(self):
        """
        Test getting jobs from all queues.
        """
        job1 = self.enqueue()
        job2 = self.enqueue()
        job3 = self.enqueue(queue="my_queue")
        jobs = helpers.call_action("job_list")
        assert len(jobs) == 3
        assert {job["id"] for job in jobs} == {job1.id, job2.id, job3.id}

    def test_specific_queues(self):
        """
        Test getting jobs from specific queues.
        """
        self.enqueue()
        job2 = self.enqueue(queue="q2")
        job3 = self.enqueue(queue="q3")
        job4 = self.enqueue(queue="q3")
        jobs = helpers.call_action("job_list", queues=["q2"])
        assert len(jobs) == 1
        assert jobs[0]["id"] == job2.id
        jobs = helpers.call_action("job_list", queues=["q2", "q3"])
        assert len(jobs) == 3
        assert {job["id"] for job in jobs} == {job2.id, job3.id, job4.id}


class TestJobShow(helpers.FunctionalRQTestBase):
    def test_existing_job(self):
        """
        Test showing an existing job.
        """
        job = self.enqueue(queue="my_queue", title="Title")
        d = helpers.call_action("job_show", id=job.id)
        assert d["id"] == job.id
        assert d["title"] == "Title"
        assert d["queue"] == "my_queue"
        assert _seconds_since_timestamp(d["created"], "%Y-%m-%dT%H:%M:%S") < 10

    def test_not_existing_job(self):
        """
        Test showing a not existing job.
        """
        with pytest.raises(logic.NotFound):
            helpers.call_action("job_show", id="does-not-exist")


def _seconds_since_timestamp(timestamp, format_):
    dt = datetime.datetime.strptime(timestamp, format_)
    now = datetime.datetime.utcnow()
    assert now > dt  # we assume timestamp is not in the future
    return (now - dt).total_seconds()
