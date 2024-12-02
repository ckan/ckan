# encoding: utf-8
import json
import datetime
from rq import get_current_job

from typing import Optional, Union, cast
from ckan.types import Context, AlchemySession

import ckan.logic as logic
import ckan.lib.search as search
import ckan.model as model

from ckan.plugins import toolkit

from logging import getLogger
log = getLogger(__name__)


def reindex_packages(package_ids: Optional[Union[list[str], None]] = None,
                     group_id: Optional[Union[str, None]] = None):
    """
    Callback for a REDIS job

    Uses task_status to track the state of a search.rebuild call.

    This always commits each record in a forceful manner.

    See ckan.lib.search.rebuild for more information.

    :param package_ids: list of package IDs to pass to search.rebuild
    :type package_ids: list

    :param group_id: organization or group ID to reindex the records
    :type group_id: string
    """
    context = cast(Context, {
        'model': model,
        'ignore_auth': True,
        'validate': False,
        'use_cache': False
    })

    _entity_id = group_id if group_id else toolkit.config.get('ckan.site_id')
    task = {
        'entity_id': _entity_id,
        'entity_type': 'group' if group_id else 'site',
        'task_type': 'reindex_packages',
        'last_updated': str(datetime.datetime.now(datetime.timezone.utc)),
        'state': 'running',
        'key': 'search_rebuild',
        'value': '{}',
        'error': '{}',
    }

    try:
        task = logic.get_action('task_status_show')(
                    context, {'entity_id': _entity_id,
                              'task_type': 'reindex_packages',
                              'key': 'search_rebuild'})
        task['state'] = 'running'
        task['last_updated'] = str(datetime.datetime.now(datetime.timezone.utc))
        logic.get_action('task_status_update')(
            {'session': cast(AlchemySession, model.meta.create_local_session()),
             'ignore_auth': True},
            task)
    except logic.NotFound:
        pass

    value = json.loads(task.get('value', '{}'))
    error = json.loads(task.get('error', '{}'))

    current_job = get_current_job()
    if current_job:
        value['job_id'] = current_job.id

    for pkg_id, total, indexed, err in search.rebuild(
      force=True, package_ids=package_ids):

        if not err:
            log.info('[%s/%s] Indexed dataset %s' % (indexed, total, pkg_id))
        else:
            log.error('[%s/%s] Failed to index dataset %s with error: %s' %
                      (indexed, total, pkg_id, err))
        value['indexed'] = indexed
        value['total'] = total
        if err:
            error[pkg_id] = err
        task['value'] = json.dumps(value)
        task['last_updated'] = str(datetime.datetime.now(datetime.timezone.utc))
        logic.get_action('task_status_update')(
            {'session': cast(AlchemySession, model.meta.create_local_session()),
             'ignore_auth': True},
            task)

    task['state'] = 'complete'
    task['last_updated'] = str(datetime.datetime.now(datetime.timezone.utc))
    logic.get_action('task_status_update')(
        {'session': cast(AlchemySession, model.meta.create_local_session()),
         'ignore_auth': True},
        task)
