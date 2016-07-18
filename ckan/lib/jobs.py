#!/usr/bin/env python
# encoding: utf-8

u'''
Asynchronous background jobs.

Note that most job management functions are not available from this
module but via the various ``job_*`` API functions.
'''

import logging

from pylons import config
from redis import ConnectionPool, Redis
from rq import Queue, Worker as RqWorker
from rq.connections import push_connection


log = logging.getLogger(__name__)

REDIS_URL_SETTING_NAME = u'ckan.jobs.redis_url'

REDIS_URL_DEFAULT_VALUE = u'redis://localhost:6379/0'

# Redis connection pool. Do not use this directly, use ``connect_to_redis``
# instead.
_connection_pool = None

# RQ job queue. Do not use this directly, use ``get_queue`` instead.
_queue = None


def connect_to_redis():
    u'''
    (Lazily) connect to Redis.

    The connection is set up but not actually established. The latter
    happens automatically once the connection is used.

    :returns: A lazy Redis connection.
    :rtype: ``redis.Redis``
    '''
    global _connection_pool
    if _connection_pool is None:
        url = config.get(REDIS_URL_SETTING_NAME, REDIS_URL_DEFAULT_VALUE)
        log.debug(u'Using Redis at {}'.format(url))
        _connection_pool = ConnectionPool.from_url(url)
    return Redis(connection_pool=_connection_pool)


def is_available():
    u'''
    Check whether Redis is available.

    :returns: The availability of Redis.
    :rtype: boolean
    '''
    redis_conn = connect_to_redis()
    try:
        return redis_conn.ping()
    except Exception:
        log.exception(u'Redis is not available')
        return False


def get_queue():
    u'''
    Get the job queue.

    The job queue is initialized if that hasn't happened before.

    :returns: The job queue.
    :rtype: ``rq.queue.Queue``
    '''
    global _queue
    if _queue is None:
        log.debug(u'Initializing the background job queue')
        redis_conn = connect_to_redis()
        _queue = Queue(connection=redis_conn)
        push_connection(redis_conn)  # https://github.com/nvie/rq/issues/479
    return _queue


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
    job = get_queue().enqueue_call(func=fn, args=args)
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
    for job in get_queue().jobs:
        if job.id == id:
            return job
    raise KeyError(u'No such job: "{}"'.format(id))


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
        u'id': job.id,
        u'title': job.meta.get(u'title'),
        u'created': job.created_at.isoformat(),
    }


def test_job(*args):
    u'''Test job.

    A test job for debugging purposes. Prints out any arguments it
    receives. Can be scheduled via ``paster jobs test``.
    '''
    print(args)


class Worker(RqWorker):
    u'''
    CKAN-specific worker.
    '''
    def __init__(self, queues=None, *args, **kwargs):
        u'''
        Constructor.

        Accepts the same arguments as the constructor of
        ``rq.worker.Worker``. However, ``queues`` defaults to the CKAN
        background job queue.
        '''
        if queues is None:
            queues = get_queue()
        super(Worker, self).__init__(queues, *args, **kwargs)

    def register_birth(self, *args, **kwargs):
        result = super(Worker, self).register_birth(*args, **kwargs)
        log.info(u'Worker {} has started (PID: {})'.format(self.key, self.pid))
        return result

    def execute_job(self, job, *args, **kwargs):
        log.info(u'Worker {} starts executing job {}'.format(self.key, job.id))
        result = super(Worker, self).execute_job(job, *args, **kwargs)
        log.info(u'Worker {} has finished executing job {}'.format(
                 self.key, job.id))
        return result

    def register_death(self, *args, **kwargs):
        result = super(Worker, self).register_death(*args, **kwargs)
        log.info(u'Worker {} has stopped'.format(self.key))
        return result

    def handle_exception(self, job, *exc_info):
        log.exception((u'Worker {} raised an exception while executing '
                      u'job {}: {}').format(self.key, job.id, exc_info[1]))
        return super(Worker, self).handle_exception(job, *exc_info)
