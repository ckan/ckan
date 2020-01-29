# encoding: utf-8

import datetime
import logging
import os
import os.path
import sys
import tempfile
import pytest
import six

from six import StringIO

import ckan.tests.helpers as helpers
from ckan.common import config

if six.PY2:
    import ckan.lib.cli as cli
    import ckan.lib.jobs as jobs
    from paste.script.command import run

log = logging.getLogger(__name__)


def paster(*args, **kwargs):
    """
    Call a paster command.

    All arguments are parsed and passed on to the command. The
    ``--config`` option is automatically appended.

    By default, an ``AssertionError`` is raised if the command exits
    with a non-zero return code or if anything is written to STDERR.
    Pass ``fail_on_error=False`` to disable this behavior.

    Example::

        code, stdout, stderr = paster(u'jobs', u'list')
        assert u'My Job Title' in stdout

        code, stdout, stderr = paster(u'jobs', u'foobar',
                                     fail_on_error=False)
        assert code == 1
        assert u'Unknown command' in stderr

    Any ``SystemExit`` raised by the command is swallowed.

    :returns: A tuple containing the return code, the content of
        STDOUT, and the content of STDERR.
    """
    fail_on_error = kwargs.pop(u"fail_on_error", True)
    args = list(args) + [u"--config=" + config[u"__file__"]]
    sys.stdout, sys.stderr = StringIO(u""), StringIO(u"")
    code = 0
    try:
        run(args)
    except SystemExit as e:
        code = e.code
    finally:
        stdout, stderr = sys.stdout.getvalue(), sys.stderr.getvalue()
        sys.stdout, sys.stderr = sys.__stdout__, sys.__stderr__
    if code != 0 and fail_on_error:
        raise AssertionError(
            u"Paster command exited with non-zero return code {}: {}".format(
                code, stderr
            )
        )
    if stderr.strip() and fail_on_error:
        raise AssertionError(
            u"Paster command wrote to STDERR: {}".format(stderr)
        )
    return code, stdout, stderr


@pytest.mark.skipif(six.PY3, reason=u"")
@pytest.mark.usefixtures("clean_db")
class TestUserAdd(object):

    """Tests for UserCmd.add"""

    @classmethod
    def setup_class(cls):
        cls.user_cmd = cli.UserCmd("user-command")

    def test_cli_user_add_valid_args(self):
        """Command shouldn't raise SystemExit when valid args are provided."""
        self.user_cmd.args = [
            "add",
            "berty",
            "password=password123",
            "fullname=Berty Guffball",
            "email=berty@example.com",
        ]
        try:
            self.user_cmd.add()
        except SystemExit:
            assert False, "SystemExit exception shouldn't be raised"

    def test_cli_user_add_no_args(self):
        """Command with no args raises SystemExit."""
        self.user_cmd.args = ["add"]
        with pytest.raises(SystemExit):
            self.user_cmd.add()

    def test_cli_user_add_no_fullname(self):
        """Command shouldn't raise SystemExit when fullname arg not present."""
        self.user_cmd.args = [
            "add",
            "berty",
            "password=password123",
            "email=berty@example.com",
        ]
        try:
            self.user_cmd.add()
        except SystemExit:
            assert False, "SystemExit exception shouldn't be raised"

    def test_cli_user_add_unicode_fullname_unicode_decode_error(self):
        """
        Command shouldn't raise UnicodeDecodeError when fullname contains
        characters outside of the ascii characterset.
        """
        self.user_cmd.args = [
            "add",
            "berty",
            "password=password123",
            "fullname=Harold Müffintøp",
            "email=berty@example.com",
        ]
        try:
            self.user_cmd.add()
        except UnicodeDecodeError:
            assert False, "UnicodeDecodeError exception shouldn't be raised"

    def test_cli_user_add_unicode_fullname_system_exit(self):
        """
        Command shouldn't raise SystemExit when fullname contains
        characters outside of the ascii characterset.
        """
        self.user_cmd.args = [
            "add",
            "berty",
            "password=password123",
            "fullname=Harold Müffintøp",
            "email=berty@example.com",
        ]
        try:
            self.user_cmd.add()
        except SystemExit:
            assert False, "SystemExit exception shouldn't be raised"


@pytest.mark.skipif(six.PY3, reason=u"")
class TestJobsUnknown(helpers.RQTestBase):
    """
    Test unknown sub-command for ``paster jobs``.
    """

    def test_unknown_command(self):
        """
        Test error handling for unknown ``paster jobs`` sub-command.
        """
        code, stdout, stderr = paster(
            u"jobs", u"does-not-exist", fail_on_error=False
        )
        assert code != 0
        assert u"Unknown command" in stderr


@pytest.mark.skipif(six.PY3, reason=u"")
class TestJobsList(helpers.RQTestBase):
    """
    Tests for ``paster jobs list``.
    """

    def test_list_default_queue(self):
        """
        Test output of ``jobs list`` for default queue.
        """
        job = self.enqueue()
        stdout = paster(u"jobs", u"list")[1]
        fields = stdout.split()
        assert len(fields) == 3
        dt = datetime.datetime.strptime(fields[0], u"%Y-%m-%dT%H:%M:%S")
        now = datetime.datetime.utcnow()
        assert abs((now - dt).total_seconds()) < 10
        assert fields[1] == job.id
        assert fields[2] == jobs.DEFAULT_QUEUE_NAME

    def test_list_other_queue(self):
        """
        Test output of ``jobs.list`` for non-default queue.
        """
        job = self.enqueue(queue=u"my_queue")
        stdout = paster(u"jobs", u"list")[1]
        fields = stdout.split()
        assert len(fields) == 3
        assert fields[2] == u"my_queue"

    def test_list_title(self):
        """
        Test title output of ``jobs list``.
        """
        job = self.enqueue(title=u"My_Title")
        stdout = paster(u"jobs", u"list")[1]
        fields = stdout.split()
        assert len(fields) == 4
        assert fields[3] == u'"My_Title"'

    def test_list_filter(self):
        """
        Test filtering by queues for ``jobs list``.
        """
        job1 = self.enqueue(queue=u"q1")
        job2 = self.enqueue(queue=u"q2")
        job3 = self.enqueue(queue=u"q3")
        stdout = paster(u"jobs", u"list", u"q1", u"q2")[1]
        assert u"q1" in stdout
        assert u"q2" in stdout
        assert u"q3" not in stdout


@pytest.mark.skipif(six.PY3, reason=u"")
class TestJobShow(helpers.RQTestBase):
    """
    Tests for ``paster jobs show``.
    """

    def test_show_existing(self):
        """
        Test ``jobs show`` for an existing job.
        """
        job = self.enqueue(queue=u"my_queue", title=u"My Title")
        stdout = paster(u"jobs", u"show", job.id)[1]
        assert job.id in stdout
        assert jobs.remove_queue_name_prefix(job.origin) in stdout

    def test_show_missing_id(self):
        """
        Test ``jobs show`` with a missing ID.
        """
        code, stdout, stderr = paster(u"jobs", u"show", fail_on_error=False)
        assert code != 0
        assert stderr


@pytest.mark.skipif(six.PY3, reason=u"")
class TestJobsCancel(helpers.RQTestBase):
    """
    Tests for ``paster jobs cancel``.
    """

    def test_cancel_existing(self):
        """
        Test ``jobs cancel`` for an existing job.
        """
        job1 = self.enqueue()
        job2 = self.enqueue()
        stdout = paster(u"jobs", u"cancel", job1.id)[1]
        all_jobs = self.all_jobs()
        assert len(all_jobs) == 1
        assert all_jobs[0].id == job2.id
        assert job1.id in stdout

    def test_cancel_not_existing(self):
        """
        Test ``jobs cancel`` for a not existing job.
        """
        code, stdout, stderr = paster(
            u"jobs", u"cancel", u"does-not-exist", fail_on_error=False
        )
        assert code != 0
        assert u"does-not-exist" in stderr

    def test_cancel_missing_id(self):
        """
        Test ``jobs cancel`` with a missing ID.
        """
        code, stdout, stderr = paster(u"jobs", u"cancel", fail_on_error=False)
        assert code != 0
        assert stderr


@pytest.mark.skipif(six.PY3, reason=u"")
class TestJobsClear(helpers.RQTestBase):
    """
    Tests for ``paster jobs clear``.
    """

    def test_clear_all_queues(self):
        """
        Test clearing all queues via ``jobs clear``.
        """
        self.enqueue()
        self.enqueue()
        self.enqueue(queue=u"q1")
        self.enqueue(queue=u"q2")
        stdout = paster(u"jobs", u"clear")[1]
        assert jobs.DEFAULT_QUEUE_NAME in stdout
        assert u"q1" in stdout
        assert u"q2" in stdout
        assert self.all_jobs() == []

    def test_clear_specific_queues(self):
        """
        Test clearing specific queues via ``jobs clear``.
        """
        job1 = self.enqueue()
        job2 = self.enqueue(queue=u"q1")
        self.enqueue(queue=u"q2")
        self.enqueue(queue=u"q2")
        self.enqueue(queue=u"q3")
        stdout = paster(u"jobs", u"clear", u"q2", u"q3")[1]
        assert u"q2" in stdout
        assert u"q3" in stdout
        assert jobs.DEFAULT_QUEUE_NAME not in stdout
        assert u"q1" not in stdout
        all_jobs = self.all_jobs()
        assert set(all_jobs) == {job1, job2}


@pytest.mark.skipif(six.PY3, reason=u"")
class TestJobsTest(helpers.RQTestBase):
    """
    Tests for ``paster jobs test``.
    """

    def test_test_default_queue(self):
        """
        Test ``jobs test`` for the default queue.
        """
        stdout = paster(u"jobs", u"test")[1]
        all_jobs = self.all_jobs()
        assert len(all_jobs) == 1
        assert (
            jobs.remove_queue_name_prefix(all_jobs[0].origin)
            == jobs.DEFAULT_QUEUE_NAME
        )

    def test_test_specific_queues(self):
        """
        Test ``jobs test`` for specific queues.
        """
        stdout = paster(u"jobs", u"test", u"q1", u"q2")[1]
        all_jobs = self.all_jobs()
        assert len(all_jobs) == 2
        assert {jobs.remove_queue_name_prefix(j.origin) for j in all_jobs} == {
            u"q1",
            u"q2",
        }


@pytest.mark.skipif(six.PY3, reason=u"")
class TestJobsWorker(helpers.RQTestBase):
    """
    Tests for ``paster jobs worker``.
    """

    # All tests of ``jobs worker`` must use the ``--burst`` option to
    # make sure that the worker exits.

    def test_worker_default_queue(self):
        """
        Test ``jobs worker`` with the default queue.
        """
        with tempfile.NamedTemporaryFile(delete=False) as f:
            self.enqueue(os.remove, args=[f.name])
            paster(u"jobs", u"worker", u"--burst")
            all_jobs = self.all_jobs()
            assert all_jobs == []
            assert not (os.path.isfile(f.name))

    def test_worker_specific_queues(self):
        """
        Test ``jobs worker`` with specific queues.
        """
        with tempfile.NamedTemporaryFile(delete=False) as f:
            with tempfile.NamedTemporaryFile(delete=False) as g:
                job1 = self.enqueue()
                job2 = self.enqueue(queue=u"q2")
                self.enqueue(os.remove, args=[f.name], queue=u"q3")
                self.enqueue(os.remove, args=[g.name], queue=u"q4")
                paster(u"jobs", u"worker", u"--burst", u"q3", u"q4")
                all_jobs = self.all_jobs()
                assert set(all_jobs) == {job1, job2}
                assert not (os.path.isfile(f.name))
                assert not (os.path.isfile(g.name))
