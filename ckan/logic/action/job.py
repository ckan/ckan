from __future__ import annotations

import logging
from typing import Any

import ckan
import ckan.logic as logic
import ckan.logic.schema
import ckan.lib.jobs as jobs
from ckan.common import asbool, config
from ckan.logic import (
    NotFound,
    check_access as _check_access,
    get_or_bust as _get_or_bust,
    side_effect_free,
)
from ckan.types import ActionResult, Context, DataDict

log = logging.getLogger('ckan.logic')


@side_effect_free
@logic.validate(ckan.logic.schema.job_list_schema)
def job_list(context: Context, data_dict: DataDict) -> ActionResult.JobList:
    '''List enqueued background jobs.

    :param list queues: Queues to list jobs from. If not given then the
        jobs from all queues are listed.

    :param int limit: Number to limit the list of jobs by.

    :param bool ids_only: Whether to return only a list if job IDs or not.

    :returns: The currently enqueued background jobs.
    :rtype: list

    Will return the list in the way that RQ workers will execute the jobs.
    Thus the left most non-empty queue will be emptied first
    before the next right non-empty one.

    .. versionadded:: 2.7
    '''
    _check_access(u'job_list', context, data_dict)
    jobs_list: ActionResult.JobList = []
    queues: Any = data_dict.get(u'queues')
    limit = data_dict.get('limit', config.get('ckan.jobs.default_list_limit',
                                              jobs.DEFAULT_JOB_LIST_LIMIT))
    ids_only = asbool(data_dict.get('ids_only', False))
    if queues:
        queues = [jobs.get_queue(q) for q in queues]
    else:
        queues = jobs.get_all_queues()
    for queue in queues:
        if ids_only:
            jobs_list += queue.job_ids[:limit]
        else:
            # type_ignore_reason: pyright does not know return from queue.jobs
            jobs_list += [jobs.dictize_job(j)  # type: ignore
                          for j in queue.jobs[:limit]]
        if limit > 0 and len(jobs_list) > limit:
            # we need to return here if there is a limit
            # and it has been surpassed
            return jobs_list[:limit]
    return jobs_list


@side_effect_free
def job_show(context: Context, data_dict: DataDict) -> ActionResult.JobShow:
    '''Show details for a background job.

    :param string id: The ID of the background job.

    :returns: Details about the background job.
    :rtype: dict

    .. versionadded:: 2.7
    '''
    _check_access(u'job_show', context, data_dict)
    id = _get_or_bust(data_dict, u'id')
    try:
        return jobs.dictize_job(jobs.job_from_id(id))
    except KeyError:
        raise NotFound


@ckan.logic.validate(ckan.logic.schema.job_clear_schema)
def job_clear(context: Context, data_dict: DataDict) -> list[str]:
    '''Clear background job queues.

    Does not affect jobs that are already being processed.

    :param list queues: The queues to clear. If not given then ALL
        queues are cleared.

    :returns: The cleared queues.
    :rtype: list

    .. versionadded:: 2.7
    '''
    _check_access(u'job_clear', context, data_dict)
    queues = data_dict.get(u'queues')
    if queues:
        queues = [jobs.get_queue(q) for q in queues]
    else:
        queues = jobs.get_all_queues()
    names = [jobs.remove_queue_name_prefix(queue.name) for queue in queues]
    for queue, name in zip(queues, names):
        queue.empty()
        log.info('Cleared background job queue "%s"', name)
    return names


def job_cancel(context: Context, data_dict: DataDict) -> None:
    '''Cancel a queued background job.

    Removes the job from the queue and deletes it.

    :param string id: The ID of the background job.

    .. versionadded:: 2.7
    '''
    _check_access(u'job_cancel', context, data_dict)
    id = _get_or_bust(data_dict, u'id')
    try:
        jobs.job_from_id(id).delete()
        log.info('Cancelled background job %s', id)
    except KeyError:
        raise NotFound
