# encoding: utf-8

from __future__ import absolute_import
import datetime
import json
import logging

import ckan.lib.jobs as rq_jobs
import ckan.lib.navl.dictization_functions
from ckan.logic import side_effect_free
import ckan.plugins as p
from dateutil.parser import parse as parse_date
from dateutil.parser import isoparse as parse_iso_date

import ckanext.xloader.schema

from . import interfaces as xloader_interfaces, jobs, db, utils

enqueue_job = p.toolkit.enqueue_job
get_queue = rq_jobs.get_queue

log = logging.getLogger(__name__)
config = p.toolkit.config

_get_or_bust = p.toolkit.get_or_bust
_validate = ckan.lib.navl.dictization_functions.validate


def xloader_submit(context, data_dict):
    ''' Submit a job to be Express Loaded. The Express Loader / 'xloader' is a
    service that imports tabular data into the datastore.

    :param resource_id: The resource id of the resource that the data
        should be imported in. The resource's URL will be used to get the data.
    :type resource_id: string
    :param set_url_type: If set to True, the ``url_type`` of the resource will
        be set to ``datastore`` and the resource URL will automatically point
        to the :ref:`datastore dump <dump>` URL. (optional, default: False)
    :type set_url_type: bool
    :param ignore_hash: If set to True, the xloader will reload the file
        even if it haven't changed. (optional, default: False)
    :type ignore_hash: bool

    Returns ``True`` if the job has been submitted and ``False`` if the job
    has not been submitted, i.e. when ckanext-xloader is not configured.

    :rtype: bool
    '''
    p.toolkit.check_access('xloader_submit', context, data_dict)
    custom_queue = data_dict.pop('queue', rq_jobs.DEFAULT_QUEUE_NAME)
    schema = context.get('schema', ckanext.xloader.schema.xloader_submit_schema())
    data_dict, errors = _validate(data_dict, schema, context)
    if errors:
        raise p.toolkit.ValidationError(errors)

    res_id = data_dict['resource_id']
    try:
        resource_dict = p.toolkit.get_action('resource_show')(context, {
            'id': res_id,
        })
    except p.toolkit.ObjectNotFound:
        return False

    for plugin in p.PluginImplementations(xloader_interfaces.IXloader):
        upload = plugin.can_upload(res_id)
        if not upload:
            msg = "Plugin {0} rejected resource {1}"\
                .format(plugin.__class__.__name__, res_id)
            log.info(msg)
            return False

    # Check if this resource is already in the process of being xloadered
    task = {
        'entity_id': res_id,
        'entity_type': 'resource',
        'task_type': 'xloader',
        'last_updated': str(datetime.datetime.utcnow()),
        'state': 'submitting',
        'key': 'xloader',
        'value': '{}',
        'error': '{}',
    }
    try:
        existing_task = p.toolkit.get_action('task_status_show')(context, {
            'entity_id': res_id,
            'task_type': 'xloader',
            'key': 'xloader'
        })
        assume_task_stale_after = datetime.timedelta(seconds=int(
            config.get('ckanext.xloader.assume_task_stale_after', 3600)))
        assume_task_stillborn_after = \
            datetime.timedelta(seconds=int(
                config.get('ckanext.xloader.assume_task_stillborn_after', 5)))
        if existing_task.get('state') == 'pending':
            import re  # here because it takes a moment to load
            queued_res_ids = [
                re.search(r"'resource_id': u?'([^']+)'",
                          job.description).groups()[0]
                for job in get_queue().get_jobs()
                if 'xloader_to_datastore' in str(job)  # filter out test_job etc
            ]
            updated = parse_iso_date(existing_task['last_updated'])
            time_since_last_updated = datetime.datetime.utcnow() - updated
            if (res_id not in queued_res_ids
                    and time_since_last_updated > assume_task_stillborn_after):
                # it's not on the queue (and if it had just been started then
                # its taken too long to update the task_status from pending -
                # the first thing it should do in the xloader job).
                # Let it be restarted.
                log.info('A pending task was found %r, but its not found in '
                         'the queue %r and is %s hours old',
                         existing_task['id'], queued_res_ids,
                         time_since_last_updated)
            elif time_since_last_updated > assume_task_stale_after:
                # it's been a while since the job was last updated - it's more
                # likely something went wrong with it and the state wasn't
                # updated than its still in progress. Let it be restarted.
                log.info('A pending task was found %r, but it is only %s hours'
                         ' old', existing_task['id'], time_since_last_updated)
            else:
                log.info('A pending task was found %s for this resource, so '
                         'skipping this duplicate task', existing_task['id'])
                return False

        task['id'] = existing_task['id']
    except p.toolkit.ObjectNotFound:
        pass

    model = context['model']

    p.toolkit.get_action('task_status_update')(
        {'session': model.meta.create_local_session(), 'ignore_auth': True},
        task
    )

    callback_url = p.toolkit.url_for(
        "api.action",
        ver=3,
        logic_function="xloader_hook",
        qualified=True
    )
    data = {
        'api_key': utils.get_xloader_user_apitoken(),
        'job_type': 'xloader_to_datastore',
        'result_url': callback_url,
        'metadata': {
            'ignore_hash': data_dict.get('ignore_hash', False),
            'ckan_url': config['ckan.site_url'],
            'resource_id': res_id,
            'set_url_type': data_dict.get('set_url_type', False),
            'task_created': task['last_updated'],
            'original_url': resource_dict.get('url'),
        }
    }
    if custom_queue != rq_jobs.DEFAULT_QUEUE_NAME:
        # Don't automatically retry if it's a custom run
        data['metadata']['tries'] = jobs.MAX_RETRIES

    # Expand timeout for resources that have to be type-guessed
    timeout = config.get(
        'ckanext.xloader.job_timeout',
        '3600' if utils.datastore_resource_exists(res_id) else '10800')
    log.debug("Timeout for XLoading resource %s is %s", res_id, timeout)

    try:
        job = enqueue_job(
            jobs.xloader_data_into_datastore, [data], queue=custom_queue,
            title="xloader_submit: package: {} resource: {}".format(resource_dict.get('package_id'), res_id),
            rq_kwargs=dict(timeout=timeout)
        )
    except Exception:
        log.exception('Unable to enqueued xloader res_id=%s', res_id)
        return False
    log.debug('Enqueued xloader job=%s res_id=%s', job.id, res_id)

    value = json.dumps({'job_id': job.id})

    task['value'] = value
    task['state'] = 'pending'
    task['last_updated'] = str(datetime.datetime.utcnow())

    p.toolkit.get_action('task_status_update')(
        {'session': model.meta.create_local_session(), 'ignore_auth': True},
        task
    )

    return True


def _enqueue(fn, args=None, kwargs=None, title=None, queue='default',
             timeout=180):
    '''Same as latest ckan.lib.jobs.enqueue - earlier CKAN versions dont have
    the timeout param

    This function can be removed when dropping support for 2.7
    '''
    if args is None:
        args = []
    if kwargs is None:
        kwargs = {}
    job = get_queue(queue).enqueue_call(func=fn, args=args, kwargs=kwargs,
                                        timeout=timeout)
    job.meta[u'title'] = title
    job.save()
    msg = u'Added background job {}'.format(job.id)
    if title:
        msg = u'{} ("{}")'.format(msg, title)
    msg = u'{} to queue "{}"'.format(msg, queue)
    log.info(msg)
    return job


def xloader_hook(context, data_dict):
    ''' Update xloader task. This action is typically called by ckanext-xloader
    whenever the status of a job changes.

    :param metadata: metadata provided when submitting job. key-value pairs.
                     Must have resource_id property.
    :type metadata: dict
    :param status: status of the job from the xloader service. Allowed values:
                   pending, running, running_but_viewable, complete, error
                   (which must all be valid values for task_status too)
    :type status: string
    :param error: Error raised during job execution
    :type error: string

    NB here are other params which are in the equivalent object in
    ckan-service-provider (from job_status):
        :param sent_data: Input data for job
        :type sent_data: json encodable data
        :param job_id: An identifier for the job
        :type job_id: string
        :param result_url: Callback url
        :type result_url: url string
        :param data: Results from job.
        :type data: json encodable data
        :param requested_timestamp: Time the job started
        :type requested_timestamp: timestamp
        :param finished_timestamp: Time the job finished
        :type finished_timestamp: timestamp

    '''

    metadata, status = _get_or_bust(data_dict, ['metadata', 'status'])

    res_id = _get_or_bust(metadata, 'resource_id')

    # Pass metadata, not data_dict, as it contains the resource id needed
    # on the auth checks
    p.toolkit.check_access('xloader_submit', context, metadata)

    task = p.toolkit.get_action('task_status_show')(context, {
        'entity_id': res_id,
        'task_type': 'xloader',
        'key': 'xloader'
    })

    task['state'] = status
    task['last_updated'] = str(datetime.datetime.utcnow())
    task['error'] = data_dict.get('error')

    resubmit = False

    if status in ('complete', 'running_but_viewable'):
        # Create default views for resource if necessary (only the ones that
        # require data to be in the DataStore)
        resource_dict = p.toolkit.get_action('resource_show')(
            context, {'id': res_id})

        dataset_dict = p.toolkit.get_action('package_show')(
            context, {'id': resource_dict['package_id']})

        for plugin in p.PluginImplementations(xloader_interfaces.IXloader):
            plugin.after_upload(context, resource_dict, dataset_dict)

        p.toolkit.get_action('resource_create_default_resource_views')(
            context,
            {
                'resource': resource_dict,
                'package': dataset_dict,
                'create_datastore_views': True,
            })

        # Check if the uploaded file has been modified in the meantime
        if (resource_dict.get('last_modified')
                and metadata.get('task_created')):
            try:
                last_modified_datetime = parse_date(
                    resource_dict['last_modified'])
                task_created_datetime = parse_date(metadata['task_created'])
                if last_modified_datetime > task_created_datetime:
                    log.debug('Uploaded file more recent: %s > %s',
                              last_modified_datetime, task_created_datetime)
                    resubmit = True
            except ValueError:
                pass
        # Check if the URL of the file has been modified in the meantime
        elif (resource_dict.get('url')
              and metadata.get('original_url')
              and resource_dict['url'] != metadata['original_url']):
            log.debug('URLs are different: %s != %s',
                      resource_dict['url'], metadata['original_url'])
            resubmit = True

    context['ignore_auth'] = True
    p.toolkit.get_action('task_status_update')(context, task)

    if resubmit:
        log.debug('Resource %s has been modified, '
                  'resubmitting to DataPusher', res_id)
        p.toolkit.get_action('xloader_submit')(
            context, {'resource_id': res_id})


@side_effect_free
def xloader_status(context, data_dict):
    ''' Get the status of a ckanext-xloader job for a certain resource.

    :param resource_id: The resource id of the resource that you want the
        status for.
    :type resource_id: string
    '''

    p.toolkit.check_access('xloader_status', context, data_dict)

    if 'id' in data_dict:
        data_dict['resource_id'] = data_dict['id']
    res_id = _get_or_bust(data_dict, 'resource_id')

    task = p.toolkit.get_action('task_status_show')(context, {
        'entity_id': res_id,
        'task_type': 'xloader',
        'key': 'xloader'
    })

    value = json.loads(task['value'])
    job_id = value.get('job_id')
    url = None
    job_detail = None

    if job_id:
        # get logs from the xloader db
        db.init(config)
        job_detail = db.get_job(job_id)

        if job_detail and job_detail.get('logs'):
            for log in job_detail['logs']:
                if 'timestamp' in log and isinstance(log['timestamp'], datetime.datetime):
                    log['timestamp'] = log['timestamp'].isoformat()
    try:
        error = json.loads(task['error'])
    except ValueError:
        # this happens occasionally, such as when the job times out
        error = task['error']
    return {
        'status': task['state'],
        'job_id': job_id,
        'job_url': url,
        'last_updated': task['last_updated'],
        'task_info': job_detail,
        'error': error,
    }
