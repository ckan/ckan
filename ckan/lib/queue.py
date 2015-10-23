from pylons import config

from rq import Queue
from redis import Redis

from logging import getLogger
log = getLogger(__name__)


queues = None


def init_queues():
    '''
    Attempt to initialise the three queues on first use. There's no need
    to create these until we need them (we might not). This will explode
    if redis is not reachable
    '''
    global queues

    connection_url = config.get(u'ckan.queues.url',
                                u'redis://localhost:6379/0')
    redis_conn = Redis.from_url(connection_url)

    try:
        queues = {
            'low': Queue('low', connection=redis_conn),
            'medium': Queue('medium', connection=redis_conn),
            'high': Queue('high', connection=redis_conn)
        }
    except Exception, e:
        log.exception(e)


def async(fn, arguments, priority='medium', timeout=30):
    '''
    Enqueue a task to be run in the background.

        :param fn: A function to be executed in the background. This
            should be imported by the caller.
        :type fn: function

        :param arguments: A list of arguments to be passed to the function,
            should be empty if there are no arguments.
        :type arguments: list

        :param priority: The priority of this task, low, medium or high.  By
            default this is medium.
        :type priority: string

        :param timeout: How long this should wait before considering
            the job lost
        :type: integer

    '''
    if not queues:
        init_queues()

    if priority not in queues.keys():
        raise ValueError("priority is not a valid value")

    job = queues[priority].enqueue_call(func=fn,
                                        args=arguments, timeout=timeout)
    log.info("Enqueued task: %r" % job)


def clear_tasks(queue_priority):
    ''' Empties the specified queue and returns the number of items
       deleted. '''
    if queues is None:
        init_queues()

    if queue_priority not in queues.keys():
        raise ValueError("priority is not a valid value")

    # We have to manually clear the queue unless we use rqinfo on the
    # command line
    counter = 0
    redis_conn = Redis()
    while True:
        job_id = redis_conn.lpop("rq:queue:%s" % queue_priority)
        if job_id is None:
            break
        redis_conn.delete("rq:job:" + job_id)
        log.info("Deleted task: %s" % job_id)
        counter += 1
    return counter


def task_count(queue_priority=None):
    '''
    Returns the number of jobs in the queue specified, which should be low,
    medium, or high. If no queue is specified, the size of all of the queues is
    returned.
    '''
    if queues is None:
        init_queues()

    if queue_priority and queue_priority not in queues.keys():
        raise ValueError("priority is not a valid value")

    size = 0
    if not queue_priority:
        size = sum(len(q.job_ids) for q in queues.values())
    else:
        size = len(queues.get(queue_priority).job_ids)
    return size
