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

    site_url = pylons.config['ckan.site_url']
    callback_url = site_url.rstrip('/') + '/api/3/action/datapusher_hook'

    user = p.toolkit.get_action('user_show')(context, {'id': context['user']})

    task = {
        'entity_id': res_id,
        'entity_type': 'resource',
        'task_type': 'datapusher',
        'last_updated': str(datetime.datetime.now()),
        'state': 'submitting',
        'key': 'datapusher',
        'value': '{}',
        'error': '{}',
    }
    try:
        task_id = p.toolkit.get_action('task_status_show')(context, {
            'entity_id': res_id,
            'task_type': 'datapusher',
            'key': 'datapusher'
        })['id']
        task['id'] = task_id
    except logic.NotFound:
        pass

    context['ignore_auth'] = True
    result = p.toolkit.get_action('task_status_update')(context, task)
    task_id = result['id']

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
                    'ckan_url': site_url,
                    'resource_id': res_id,
                    'set_url_type': data_dict.get('set_url_type', False)
                }
            }))
        r.raise_for_status()
    except requests.exceptions.ConnectionError, e:
        error = {'message': 'Could not connect to DataPusher.',
                 'details': str(e)}
        task['error'] = json.dumps(error)
        task['state'] = 'error'
        task['last_updated'] = str(datetime.datetime.now()),
        p.toolkit.get_action('task_status_update')(context, task)
        raise p.toolkit.ValidationError(error)

    except requests.exceptions.HTTPError, e:
        m = 'An Error occurred while sending the job: {0}'.format(e.message)
        try:
            body = e.response.json()
        except ValueError:
            body = e.response.text
        error = {'message': m,
                 'details': body,
                 'status_code': r.status_code}
        task['error'] = json.dumps(error)
        task['state'] = 'error'
        task['last_updated'] = str(datetime.datetime.now()),
        p.toolkit.get_action('task_status_update')(context, task)
        raise p.toolkit.ValidationError(error)

    value = json.dumps({'job_id': r.json()['job_id'],
                        'job_key': r.json()['job_key']})

    task['value'] = value
    task['state'] = 'pending'
    task['last_updated'] = str(datetime.datetime.now()),
    p.toolkit.get_action('task_status_update')(context, task)

    return True


def datapusher_hook(context, data_dict):
    ''' Update datapusher task. This action is typically called by the
    datapusher whenever the status of a job changes.

    :param metadata: metadata produced by datapuser service must have
       resource_id property.
    :type metadata: dict
    :param status: status of the job from the datapusher service
    :type status: string
    '''

    metadata, status = _get_or_bust(data_dict, ['metadata', 'status'])

    res_id = _get_or_bust(metadata, 'resource_id')

    # Pass metadata, not data_dict, as it contains the resource id needed
    # on the auth checks
    p.toolkit.check_access('datapusher_submit', context, metadata)

    task = p.toolkit.get_action('task_status_show')(context, {
        'entity_id': res_id,
        'task_type': 'datapusher',
        'key': 'datapusher'
    })

    task['state'] = status
    task['last_updated'] = str(datetime.datetime.now())

    context['ignore_auth'] = True
    p.toolkit.get_action('task_status_update')(context, task)


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

    task = p.toolkit.get_action('task_status_show')(context, {
        'entity_id': res_id,
        'task_type': 'datapusher',
        'key': 'datapusher'
    })

    datapusher_url = pylons.config.get('ckan.datapusher.url')
    if not datapusher_url:
        raise p.toolkit.ValidationError(
            {'configuration': ['ckan.datapusher.url not in config file']})

    value = json.loads(task['value'])
    job_key = value.get('job_key')
    job_id = value.get('job_id')
    url = None
    job_detail = None

    if job_id:
        url = urlparse.urljoin(datapusher_url, 'job' + '/' + job_id)
        try:
            r = requests.get(url, headers={'Content-Type': 'application/json',
                                           'Authorization': job_key})
            r.raise_for_status()
            job_detail = r.json()
        except (requests.exceptions.ConnectionError,
                requests.exceptions.HTTPError), e:
            job_detail = {'error': 'cannot connect to datapusher'}

    return {
        'status': task['state'],
        'job_id': job_id,
        'job_url': url,
        'last_updated': task['last_updated'],
        'job_key': job_key,
        'task_info': job_detail,
        'error': json.loads(task['error'])
    }
