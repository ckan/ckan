#!/usr/bin/env python
# encoding: utf-8

u'''
Asynchronous background jobs.

Note that most job management functions are not available from this
module but via the various ``job_*`` API functions.

Internally, RQ queue names are prefixed with a string containing the
CKAN site ID to avoid key collisions when the same Redis database is
used for multiple CKAN instances. The functions of this module expect
unprefixed queue names (e.g. ``'default'``) unless noted otherwise. The
raw RQ objects (e.g. a queue returned by ``get_queue``) use the full,
prefixed names. Use the functions ``add_queue_name_prefix`` and
``remove_queue_name_prefix`` to manage queue name prefixes.
'''

import logging

from pylons import config
from redis import ConnectionPool, Redis
from rq import Queue, Worker as RqWorker
from rq.connections import push_connection
from rq.utils import ensure_list


log = logging.getLogger(__name__)

REDIS_URL_SETTING_NAME = u'redis_url'

REDIS_URL_DEFAULT_VALUE = u'redis://localhost:6379/0'

DEFAULT_QUEUE_NAME = u'default'

# Redis connection pool. Do not use this directly, use ``connect_to_redis``
# instead.
_connection_pool = None

# RQ job queues. Do not use this directly, use ``get_queue`` instead.
_queues = {}


def get_queue_name_prefix():
    u'''
    Get the queue name prefix.
    '''
    # This must be done at runtime since we need a loaded config
    return u'ckan:{}:'.format(config[u'ckan.site_id'])


def add_queue_name_prefix(name):
    u'''
    Prefix a queue name.

    .. seealso:: :py:func:`remove_queue_name_prefix`
    '''
    return get_queue_name_prefix() + name


def remove_queue_name_prefix(name):
    u'''
    Remove a queue name's prefix.

    .. seealso:: :py:func:`add_queue_name_prefix`
    '''
    prefix = get_queue_name_prefix()
    if name.startswith(prefix):
        name = name[len(prefix):]
    return name


def connect_to_redis():
    u'''
    (Lazily) connect to Redis.

    The connection is set up but not actually established. The latter
    happens automatically once the connection is used.

    :returns: A lazy Redis connection.
    :rtype: ``redis.Redis``

    .. seealso:: :py:func:`is_available`
    '''
    global _connection_pool
    if _connection_pool is None:
        url = config.get(REDIS_URL_SETTING_NAME, REDIS_URL_DEFAULT_VALUE)
        log.debug(u'Using Redis at {}'.format(url))
        _connection_pool = ConnectionPool.from_url(url)
    conn = Redis(connection_pool=_connection_pool)
    push_connection(conn)  # https://github.com/nvie/rq/issues/479
    return conn


def is_available():
    u'''
    Check whether Redis is available.

    :returns: The availability of Redis.
    :rtype: boolean

    .. seealso:: :py:func:`connect_to_redis`
    '''
    redis_conn = connect_to_redis()
    try:
        return redis_conn.ping()
    except Exception:
        log.exception(u'Redis is not available')
        return False


def get_all_queues():
    u'''
    Return all job queues.

    :returns: A list of all queues.
    :rtype: List of ``rq.queue.Queue`` instances

    .. seealso:: :py:func:`get_queue`
    '''
    redis_conn = connect_to_redis()
    prefix = get_queue_name_prefix()
    return [q for q in Queue.all(connection=redis_conn) if
            q.name.startswith(prefix)]


def get_queue(name=DEFAULT_QUEUE_NAME):
    u'''
    Get a job queue.

    The job queue is initialized if that hasn't happened before.

    :param string name: The name of the queue. If not given then the
        default queue is returned.

    :returns: The job queue.
    :rtype: ``rq.queue.Queue``

    .. seealso:: :py:func:`get_all_queues`
    '''
    global _queues
    fullname = add_queue_name_prefix(name)
    try:
        return _queues[fullname]
    except KeyError:
        log.debug(u'Initializing background job queue "{}"'.format(name))
        redis_conn = connect_to_redis()
        queue = _queues[fullname] = Queue(fullname, connection=redis_conn)
        return queue


def enqueue(fn, args=None, title=None, queue=DEFAULT_QUEUE_NAME):
    u'''
    Enqueue a job to be run in the background.

    :param function fn: Function to be executed in the background

    :param list args: List of arguments to be passed to the function.
        Pass an empty list if there are no arguments (default).

    :param string title: Optional human-readable title of the job.

    :param string queue: Name of the queue. If not given then the
        default queue is used.

    :returns: The enqueued job.
    :rtype: ``rq.job.Job``
    '''
    if args is None:
        args = []
    job = get_queue(queue).enqueue_call(func=fn, args=args)
    job.meta[u'title'] = title
    job.save()
    msg = u'Added background job {}'.format(job.id)
    if title:
        msg = u'{} ("{}")'.format(msg, title)
    msg = u'{} to queue "{}"'.format(msg, queue)
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
    for queue in get_all_queues():
        for job in queue.jobs:
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
        u'queue': remove_queue_name_prefix(job.origin),
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
        ``rq.worker.Worker``. However, the behavior of the ``queues``
        parameter is different.

        :param queues: The job queue(s) to listen on. Can be a string
            with the name of a single queue or a list of queue names.
            If not given then the default queue is used.
        '''
        queues = queues or [DEFAULT_QUEUE_NAME]
        queues = [get_queue(q) for q in ensure_list(queues)]
        super(Worker, self).__init__(queues, *args, **kwargs)

    def register_birth(self, *args, **kwargs):
        result = super(Worker, self).register_birth(*args, **kwargs)
        names = [remove_queue_name_prefix(n) for n in self.queue_names()]
        names = u', '.join(u'"{}"'.format(n) for n in names)
        log.info(u'Worker {} (PID {}) has started on queue(s) {} '.format(
                 self.key, self.pid, names))
        return result

    def execute_job(self, job, *args, **kwargs):
        queue = remove_queue_name_prefix(job.origin)
        log.info(u'Worker {} starts executing job {} from queue "{}"'.format(
                 self.key, job.id, queue))
        result = super(Worker, self).execute_job(job, *args, **kwargs)
        log.info(u'Worker {} has finished executing job {}'.format(
                 self.key, job.id))
        return result

    def register_death(self, *args, **kwargs):
        result = super(Worker, self).register_death(*args, **kwargs)
        log.info(u'Worker {} (PID {}) has stopped'.format(self.key, self.pid))
        return result

    def handle_exception(self, job, *exc_info):
        log.exception((u'Worker {} raised an exception while executing '
                      u'job {}: {}').format(self.key, job.id, exc_info[1]))
        return super(Worker, self).handle_exception(job, *exc_info)
