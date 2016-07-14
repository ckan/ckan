#!/usr/bin/env python
# encoding: utf-8

u'''
Asynchronous background jobs.

Note that most job management functions are not available from this
module but via the various ``job_*`` API functions.
'''

import logging

from pylons import config
from redis import Redis
from rq import Queue, Worker as RqWorker
from rq.connections import push_connection


log = logging.getLogger(__name__)

REDIS_URL_SETTING_NAME = u'ckan.jobs.redis_url'

REDIS_URL_DEFAULT_VALUE = u'redis://localhost:6379/0'

queue = None


def init_queue():
    u'''
    Initialize the job queue.

    :returns: The queue.
    :rtype: ``rq.queue.Queue``
    '''
    global queue
    if queue is not None:
        return
    redis_url = config.get(REDIS_URL_SETTING_NAME, REDIS_URL_DEFAULT_VALUE)
    log.warn(u'Initializing background job queue at {}'.format(redis_url))
    redis_conn = Redis.from_url(redis_url)
    redis_conn.ping()  # Force connection check
    queue = Queue(connection=redis_conn)
    push_connection(redis_conn)  # See https://github.com/nvie/rq/issues/479
    return queue


def enqueue(fn, args=None, title=None):
    u'''
    Enqueue a job to be run in the background.

    :param function fn: Function to be executed in the background

    :param list args: List of arguments to be passed to the function.
        Pass an empty list if there are no arguments (default).

    :param string title: Optional human-readable title of the job.

    :returns: The enqueued job.
    :rtype: ``rq.job.Job``
    '''
    if args is None:
        args = []
    job = queue.enqueue_call(func=fn, args=args)
    job.meta[u'title'] = title
    job.save()
    if title:
        msg = u'Enqueued background job "{}" ({})'.format(title, job.id)
    else:
        msg = u'Enqueued background job {}'.format(job.id)
    log.info(msg)
    return job


def from_id(id):
    u'''
    Look up an enqueued job by its ID.

    :param string id: The ID of the job.

    :returns: The job.
    :rtype: ``rq.job.Job``

    :raises KeyError: if no job with that ID exists.
    '''
    for job in queue.jobs:
        if job.id == id:
            return job
    raise KeyError('No such job: "{}"'.format(id))


def dictize_job(job):
    u'''Convert a job to a dict.

    In contrast to ``rq.job.Job.to_dict`` this function includes only
    the attributes that are relevant to our use case and promotes the
    meta attributes that we use (e.g. ``title``).

    :param rq.job.Job job: The job to dictize.

    :returns: The dictized job.
    :rtype: dict
    '''
    return {
        'id': job.id,
        'title': job.meta.get('title'),
        'created': job.created_at.isoformat(),
    }


def test_job(*args):
    u'''Test job.

    A test job for debugging purposes. Prints out any arguments it
    receives.
    '''
    print(args)


class Worker(RqWorker):
    u'''
    Custom worker with CKAN-specific logging.
    '''
    def register_birth(self, *args, **kwargs):
        result = super(Worker, self).register_birth(*args, **kwargs)
        log.info('Worker {} has started (PID: {})'.format(self.key, self.pid))
        return result

    def execute_job(self, job, *args, **kwargs):
        log.info('Worker {} starts to execute job {}'.format(self.key, job.id))
        result = super(Worker, self).execute_job(job, *args, **kwargs)
        log.info('Worker {} has finished executing job {}'.format(self.key, job.id))
        return result

    def register_death(self, *args, **kwargs):
        result = super(Worker, self).register_death(*args, **kwargs)
        log.info('Worker {} has stopped'.format(self.key))
        return result
