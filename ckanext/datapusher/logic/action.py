import logging
import json
import urlparse
import datetime

import pylons
import requests

import ckan.lib.navl.dictization_functions
import ckan.logic as logic
import ckan.plugins as p
import ckanext.datapusher.logic.schema as dpschema

log = logging.getLogger(__name__)
_get_or_bust = logic.get_or_bust
_validate = ckan.lib.navl.dictization_functions.validate


def datapusher_submit(context, data_dict):
    ''' Submit a job to the datapusher. The datapusher is a service that
    imports tabular data into the datastore.

    :param resource_id: The resource id of the resource that the data
        should be imported in. The resource's URL will be used to get the data.
    :type resource_id: string
    :param set_url_type: If set to True, the ``url_type`` of the resource will
        be set to ``datastore`` and the resource URL will automatically point
        to the :ref:`datastore dump <dump>` URL. (optional, default: False)
    :type set_url_type: bool

    Returns ``True`` if the job has been submitted and ``False`` if the job
    has not been submitted, i.e. when the datapusher is not configured.

    :rtype: bool
    '''

    schema = context.get('schema', dpschema.datapusher_submit_schema())
    data_dict, errors = _validate(data_dict, schema, context)
    if errors:
        raise p.toolkit.ValidationError(errors)

    res_id = data_dict['resource_id']

    p.toolkit.check_access('datapusher_submit', context, data_dict)

    datapusher_url = pylons.config.get('ckan.datapusher.url')

    callback_url = p.toolkit.url_for(
        controller='api', action='action', logic_function='datapusher_hook',
        ver=3, qualified=True)

    user = p.toolkit.get_action('user_show')(context, {'id': context['user']})

    try:
        r = requests.post(
            urlparse.urljoin(datapusher_url, 'job'),
            headers={
                'Content-Type': 'application/json'
            },
            data=json.dumps({
                'api_key': user['apikey'],
                'job_type': 'push_to_datastore',
                'result_url': callback_url,
                'metadata': {
                    'ckan_url': pylons.config['ckan.site_url'],
                    'resource_id': res_id,
                    'set_url_type': data_dict.get('set_url_type', False)
                }
            }))
        r.raise_for_status()
    except requests.exceptions.ConnectionError, e:
        raise p.toolkit.ValidationError({'datapusher': {
            'message': 'Could not connect to DataPusher.',
            'details': str(e)}})
    except requests.exceptions.HTTPError, e:
        m = 'An Error occurred while sending the job: {0}'.format(e.message)
        try:
            body = e.response.json()
        except ValueError:
            body = e.response.text
        raise p.toolkit.ValidationError({'datapusher': {
            'message': m,
            'details': body,
            'status_code': r.status_code}})

    empty_task = {
        'entity_id': res_id,
        'entity_type': 'resource',
        'task_type': 'datapusher',
        'last_updated': str(datetime.datetime.now()),
        'state': 'pending'
    }

    tasks = []
    for (k, v) in [('job_id', r.json()['job_id']),
                   ('job_key', r.json()['job_key'])]:
        t = empty_task.copy()
        t['key'] = k
        t['value'] = v
        tasks.append(t)
    p.toolkit.get_action('task_status_update_many')(context, {'data': tasks})

    return True


def datapusher_hook(context, data_dict):
    ''' Update datapusher task. This action is typically called by the
    datapusher whenever the status of a job changes.

    Expects a job with ``status`` and ``metadata`` with a ``resource_id``.
    '''

    # TODO: use a schema to validate

    p.toolkit.check_access('datapusher_submit', context, data_dict)

    res_id = data_dict['metadata']['resource_id']

    task_id = p.toolkit.get_action('task_status_show')(context, {
        'entity_id': res_id,
        'task_type': 'datapusher',
        'key': 'job_id'
    })

    task_key = p.toolkit.get_action('task_status_show')(context, {
        'entity_id': res_id,
        'task_type': 'datapusher',
        'key': 'job_key'
    })

    tasks = [task_id, task_key]

    for task in tasks:
        task['state'] = data_dict['status']
        task['last_updated'] = str(datetime.datetime.now())

    p.toolkit.get_action('task_status_update_many')(context, {'data': tasks})


def datapusher_status(context, data_dict):
    ''' Get the status of a datapusher job for a certain resource.

    :param resource_id: The resource id of the resource that you want the
        datapusher status for.
    :type resource_id: string
    '''

    p.toolkit.check_access('datapusher_status', context, data_dict)

    if 'id' in data_dict:
        data_dict['resource_id'] = data_dict['id']
    res_id = _get_or_bust(data_dict, 'resource_id')

    task_id = p.toolkit.get_action('task_status_show')(context, {
        'entity_id': res_id,
        'task_type': 'datapusher',
        'key': 'job_id'
    })

    task_key = p.toolkit.get_action('task_status_show')(context, {
        'entity_id': res_id,
        'task_type': 'datapusher',
        'key': 'job_key'
    })

    datapusher_url = pylons.config.get('ckan.datapusher.url')
    if not datapusher_url:
        raise p.toolkit.ValidationError(
            {'configuration': ['DataPusher not configured.']})

    url = urlparse.urljoin(datapusher_url, 'job' + '/' + task_id['value'])
    return {
        'status': task_id['state'],
        'job_id': task_id['value'],
        'job_url': url,
        'last_updated': task_id['last_updated'],
        'job_key': task_key['value']
    }
