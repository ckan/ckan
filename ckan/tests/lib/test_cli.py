# encoding: utf-8

import datetime
import logging
import os
import os.path
from StringIO import StringIO
import sys
import tempfile

from nose.tools import (assert_raises, eq_ as eq, ok_ as ok, assert_in,
                        assert_not_in, assert_not_equal as neq, assert_false as nok)
from paste.script.command import run

import ckan.lib.cli as cli
import ckan.lib.jobs as jobs
import ckan.tests.helpers as helpers
from ckan.common import config

log = logging.getLogger(__name__)


def paster(*args, **kwargs):
    '''
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
    '''
    fail_on_error = kwargs.pop(u'fail_on_error', True)
    args = list(args) + [u'--config=' + config[u'__file__']]
    sys.stdout, sys.stderr = StringIO(u''), StringIO(u'')
    code = 0
    try:
        run(args)
    except SystemExit as e:
        code = e.code
    finally:
        stdout, stderr = sys.stdout.getvalue(), sys.stderr.getvalue()
        sys.stdout, sys.stderr = sys.__stdout__, sys.__stderr__
    if code != 0 and fail_on_error:
        raise AssertionError(u'Paster command exited with non-zero return code {}: {}'.format(code, stderr))
    if stderr.strip() and fail_on_error:
        raise AssertionError(u'Paster command wrote to STDERR: {}'.format(stderr))
    return code, stdout, stderr


class TestUserAdd(object):

    '''Tests for UserCmd.add'''

    @classmethod
    def setup_class(cls):
        cls.user_cmd = cli.UserCmd('user-command')

    def setup(self):
        helpers.reset_db()

    def test_cli_user_add_valid_args(self):
        '''Command shouldn't raise SystemExit when valid args are provided.'''
        self.user_cmd.args = ['add', 'berty', 'password=password123',
                              'fullname=Berty Guffball',
                              'email=berty@example.com']
        try:
            self.user_cmd.add()
        except SystemExit:
            assert False, "SystemExit exception shouldn't be raised"

    def test_cli_user_add_no_args(self):
        '''Command with no args raises SystemExit.'''
        self.user_cmd.args = ['add', ]
        assert_raises(SystemExit, self.user_cmd.add)

    def test_cli_user_add_no_fullname(self):
        '''Command shouldn't raise SystemExit when fullname arg not present.'''
        self.user_cmd.args = ['add', 'berty', 'password=password123',
                              'email=berty@example.com']
        try:
            self.user_cmd.add()
        except SystemExit:
            assert False, "SystemExit exception shouldn't be raised"

    def test_cli_user_add_unicode_fullname_unicode_decode_error(self):
        '''
        Command shouldn't raise UnicodeDecodeError when fullname contains
        characters outside of the ascii characterset.
        '''
        self.user_cmd.args = ['add', 'berty', 'password=password123',
                              'fullname=Harold Müffintøp',
                              'email=berty@example.com']
        try:
            self.user_cmd.add()
        except UnicodeDecodeError:
            assert False, "UnicodeDecodeError exception shouldn't be raised"

    def test_cli_user_add_unicode_fullname_system_exit(self):
        '''
        Command shouldn't raise SystemExit when fullname contains
        characters outside of the ascii characterset.
        '''
        self.user_cmd.args = ['add', 'berty', 'password=password123',
                              'fullname=Harold Müffintøp',
                              'email=berty@example.com']
        try:
            self.user_cmd.add()
        except SystemExit:
            assert False, "SystemExit exception shouldn't be raised"


class TestJobsUnknown(helpers.RQTestBase):
    '''
    Test unknown sub-command for ``paster jobs``.
    '''
    def test_unknown_command(self):
        '''
        Test error handling for unknown ``paster jobs`` sub-command.
        '''
        code, stdout, stderr = paster(u'jobs', u'does-not-exist',
                                      fail_on_error=False)
        neq(code, 0)
        assert_in(u'Unknown command', stderr)


class TestJobsList(helpers.RQTestBase):
    '''
    Tests for ``paster jobs list``.
    '''
    def test_list_default_queue(self):
        '''
        Test output of ``jobs list`` for default queue.
        '''
        job = self.enqueue()
        stdout = paster(u'jobs', u'list')[1]
        fields = stdout.split()
        eq(len(fields), 3)
        dt = datetime.datetime.strptime(fields[0], u'%Y-%m-%dT%H:%M:%S')
        now = datetime.datetime.utcnow()
        ok(abs((now - dt).total_seconds()) < 10)
        eq(fields[1], job.id)
        eq(fields[2], jobs.DEFAULT_QUEUE_NAME)

    def test_list_other_queue(self):
        '''
        Test output of ``jobs.list`` for non-default queue.
        '''
        job = self.enqueue(queue=u'my_queue')
        stdout = paster(u'jobs', u'list')[1]
        fields = stdout.split()
        eq(len(fields), 3)
        eq(fields[2], u'my_queue')

    def test_list_title(self):
        '''
        Test title output of ``jobs list``.
        '''
        job = self.enqueue(title=u'My_Title')
        stdout = paster(u'jobs', u'list')[1]
        fields = stdout.split()
        eq(len(fields), 4)
        eq(fields[3], u'"My_Title"')

    def test_list_filter(self):
        '''
        Test filtering by queues for ``jobs list``.
        '''
        job1 = self.enqueue(queue=u'q1')
        job2 = self.enqueue(queue=u'q2')
        job3 = self.enqueue(queue=u'q3')
        stdout = paster(u'jobs', u'list', u'q1', u'q2')[1]
        assert_in(u'q1', stdout)
        assert_in(u'q2', stdout)
        assert_not_in(u'q3', stdout)


class TestJobShow(helpers.RQTestBase):
    '''
    Tests for ``paster jobs show``.
    '''
    def test_show_existing(self):
        '''
        Test ``jobs show`` for an existing job.
        '''
        job = self.enqueue(queue=u'my_queue', title=u'My Title')
        stdout = paster(u'jobs', u'show', job.id)[1]
        assert_in(job.id, stdout)
        assert_in(jobs.remove_queue_name_prefix(job.origin), stdout)

    def test_show_missing_id(self):
        '''
        Test ``jobs show`` with a missing ID.
        '''
        code, stdout, stderr = paster(u'jobs', u'show', fail_on_error=False)
        neq(code, 0)
        ok(stderr)


class TestJobsCancel(helpers.RQTestBase):
    '''
    Tests for ``paster jobs cancel``.
    '''
    def test_cancel_existing(self):
        '''
        Test ``jobs cancel`` for an existing job.
        '''
        job1 = self.enqueue()
        job2 = self.enqueue()
        stdout = paster(u'jobs', u'cancel', job1.id)[1]
        all_jobs = self.all_jobs()
        eq(len(all_jobs), 1)
        eq(all_jobs[0].id, job2.id)
        assert_in(job1.id, stdout)

    def test_cancel_not_existing(self):
        '''
        Test ``jobs cancel`` for a not existing job.
        '''
        code, stdout, stderr = paster(u'jobs', u'cancel', u'does-not-exist',
                                      fail_on_error=False)
        neq(code, 0)
        assert_in(u'does-not-exist', stderr)

    def test_cancel_missing_id(self):
        '''
        Test ``jobs cancel`` with a missing ID.
        '''
        code, stdout, stderr = paster(u'jobs', u'cancel', fail_on_error=False)
        neq(code, 0)
        ok(stderr)


class TestJobsClear(helpers.RQTestBase):
    '''
    Tests for ``paster jobs clear``.
    '''
    def test_clear_all_queues(self):
        '''
        Test clearing all queues via ``jobs clear``.
        '''
        self.enqueue()
        self.enqueue()
        self.enqueue(queue=u'q1')
        self.enqueue(queue=u'q2')
        stdout = paster(u'jobs', u'clear')[1]
        assert_in(jobs.DEFAULT_QUEUE_NAME, stdout)
        assert_in(u'q1', stdout)
        assert_in(u'q2', stdout)
        eq(self.all_jobs(), [])

    def test_clear_specific_queues(self):
        '''
        Test clearing specific queues via ``jobs clear``.
        '''
        job1 = self.enqueue()
        job2 = self.enqueue(queue=u'q1')
        self.enqueue(queue=u'q2')
        self.enqueue(queue=u'q2')
        self.enqueue(queue=u'q3')
        stdout = paster(u'jobs', u'clear', u'q2', u'q3')[1]
        assert_in(u'q2', stdout)
        assert_in(u'q3', stdout)
        assert_not_in(jobs.DEFAULT_QUEUE_NAME, stdout)
        assert_not_in(u'q1', stdout)
        all_jobs = self.all_jobs()
        eq(set(all_jobs), {job1, job2})


class TestJobsTest(helpers.RQTestBase):
    '''
    Tests for ``paster jobs test``.
    '''
    def test_test_default_queue(self):
        '''
        Test ``jobs test`` for the default queue.
        '''
        stdout = paster(u'jobs', u'test')[1]
        all_jobs = self.all_jobs()
        eq(len(all_jobs), 1)
        eq(jobs.remove_queue_name_prefix(all_jobs[0].origin),
           jobs.DEFAULT_QUEUE_NAME)

    def test_test_specific_queues(self):
        '''
        Test ``jobs test`` for specific queues.
        '''
        stdout = paster(u'jobs', u'test', u'q1', u'q2')[1]
        all_jobs = self.all_jobs()
        eq(len(all_jobs), 2)
        eq({jobs.remove_queue_name_prefix(j.origin) for j in all_jobs},
           {u'q1', u'q2'})


class TestJobsWorker(helpers.RQTestBase):
    '''
    Tests for ``paster jobs worker``.
    '''
    # All tests of ``jobs worker`` must use the ``--burst`` option to
    # make sure that the worker exits.

    def test_worker_default_queue(self):
        '''
        Test ``jobs worker`` with the default queue.
        '''
        with tempfile.NamedTemporaryFile(delete=False) as f:
            self.enqueue(os.remove, args=[f.name])
            paster(u'jobs', u'worker', u'--burst')
            all_jobs = self.all_jobs()
            eq(all_jobs, [])
            nok(os.path.isfile(f.name))

    def test_worker_specific_queues(self):
        '''
        Test ``jobs worker`` with specific queues.
        '''
        with tempfile.NamedTemporaryFile(delete=False) as f:
            with tempfile.NamedTemporaryFile(delete=False) as g:
                job1 = self.enqueue()
                job2 = self.enqueue(queue=u'q2')
                self.enqueue(os.remove, args=[f.name], queue=u'q3')
                self.enqueue(os.remove, args=[g.name], queue=u'q4')
                paster(u'jobs', u'worker', u'--burst', u'q3', u'q4')
                all_jobs = self.all_jobs()
                eq(set(all_jobs), {job1, job2})
                nok(os.path.isfile(f.name))
                nok(os.path.isfile(g.name))
