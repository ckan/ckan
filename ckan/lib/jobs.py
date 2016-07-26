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
from rq import Queue, Worker as RqWorker
from rq.connections import push_connection
from rq.exceptions import NoSuchJobError
from rq.job import Job
from rq.utils import ensure_list

from ckan.lib.redis import connect_to_redis


log = logging.getLogger(__name__)

DEFAULT_QUEUE_NAME = u'default'

# RQ job queues. Do not use this directly, use ``get_queue`` instead.
_queues = {}


def _connect():
    u'''
    Connect to Redis and tell RQ about it.

    Workaround for https://github.com/nvie/rq/issues/479.
    '''
    conn = connect_to_redis()
    push_connection(conn)
    return conn


def _get_queue_name_prefix():
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
    return _get_queue_name_prefix() + name


def remove_queue_name_prefix(name):
    u'''
    Remove a queue name's prefix.

    :raises ValueError: if the given name is not prefixed.

    .. seealso:: :py:func:`add_queue_name_prefix`
    '''
    prefix = _get_queue_name_prefix()
    if not name.startswith(prefix):
        raise ValueError(u'Queue name "{}" is not prefixed.'.format(name))
    return name[len(prefix):]


def get_all_queues():
    u'''
    Return all job queues currently in use.

    :returns: The queues.
    :rtype: List of ``rq.queue.Queue`` instances

    .. seealso:: :py:func:`get_queue`
    '''
    redis_conn = _connect()
    prefix = _get_queue_name_prefix()
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
        redis_conn = _connect()
        queue = _queues[fullname] = Queue(fullname, connection=redis_conn)
        return queue


def enqueue(fn, args=None, kwargs=None, title=None, queue=DEFAULT_QUEUE_NAME):
    u'''
    Enqueue a job to be run in the background.

    :param function fn: Function to be executed in the background

    :param list args: List of arguments to be passed to the function.
        Pass an empty list if there are no arguments (default).

    :param dict kwargs: Dict of keyword arguments to be passed to the
        function. Pass an empty dict if there are no keyword arguments
        (default).

    :param string title: Optional human-readable title of the job.

    :param string queue: Name of the queue. If not given then the
        default queue is used.

    :returns: The enqueued job.
    :rtype: ``rq.job.Job``
    '''
    if args is None:
        args = []
    if kwargs is None:
        kwargs = {}
    job = get_queue(queue).enqueue_call(func=fn, args=args, kwargs=kwargs)
    job.meta[u'title'] = title
    job.save()
    msg = u'Added background job {}'.format(job.id)
    if title:
        msg = u'{} ("{}")'.format(msg, title)
    msg = u'{} to queue "{}"'.format(msg, queue)
    log.info(msg)
    return job


def job_from_id(id):
    u'''
    Look up an enqueued job by its ID.

    :param string id: The ID of the job.

    :returns: The job.
    :rtype: ``rq.job.Job``

    :raises KeyError: if no job with that ID exists.
    '''
    try:
        return Job.fetch(id, connection=_connect())
    except NoSuchJobError:
        raise KeyError(u'There is no job with ID "{}".'.format(id))


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
        u'created': job.created_at.strftime(u'%Y-%m-%dT%H:%M:%S'),
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
        log.info(u'Worker {} has started job {} from queue "{}"'.format(
                 self.key, job.id, queue))
        result = super(Worker, self).execute_job(job, *args, **kwargs)
        log.info(u'Worker {} has finished job {} from queue "{}"'.format(
                 self.key, job.id, queue))
        return result

    def register_death(self, *args, **kwargs):
        result = super(Worker, self).register_death(*args, **kwargs)
        log.info(u'Worker {} (PID {}) has stopped'.format(self.key, self.pid))
        return result

    def handle_exception(self, job, *exc_info):
        log.exception(u'Job {} on worker {} raised an exception: {}'.format(
                      job.id, self.key, exc_info[1]))
        return super(Worker, self).handle_exception(job, *exc_info)
