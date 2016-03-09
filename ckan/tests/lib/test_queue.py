# -*- coding: utf-8 -*-
import logging
from nose.tools import raises

import ckan.tests.helpers as helpers
import ckan.lib.queue as queue

log = logging.getLogger(__name__)


def fake_function():
    return 42


class TestTasks(object):

    def setup(self):
        queue.clear_tasks('low')
        queue.clear_tasks('medium')
        queue.clear_tasks('high')

    def test_simple_async(self):
        queue.async(fake_function, [])
        assert queue.task_count('medium') == 1

    @raises(ValueError)
    def test_failing_async_bad_priority(self):
        queue.async(fake_function, [], priority="immediately")

    def test_queue_size(self):
        queue.async(fake_function, [], priority='low')
        queue.async(fake_function, [], priority='low')
        queue.async(fake_function, [], priority='low')
        assert task.task_count('low') == 3
        queue.clear_queue('low')
        assert queue.task_count('low') == 0

    @raises(ValueError)
    def test_queue_size_invalid(self):
        assert queue.task_count('immediately') == 0

    def test_queue_size(self):
        queue.async(fake_function, [], priority='low')
        queue.async(fake_function, [], priority='medium')
        queue.async(fake_function, [], priority='high')
        assert queue.task_count() == 3
