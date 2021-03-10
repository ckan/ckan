# encoding: utf-8

import logging
import json
import datetime
import time

from six.moves.urllib.parse import urljoin
from dateutil.parser import parse as parse_date

import requests

import ckan.lib.helpers as h
import ckan.lib.navl.dictization_functions
import ckan.logic as logic
import ckan.plugins as p
from ckan.common import config
import ckanext.datapusher.logic.schema as dpschema
import ckanext.datapusher.interfaces as interfaces

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
    :param ignore_hash: If set to True, the datapusher will reload the file
        even if it haven't changed. (optional, default: False)
    :type ignore_hash: bool

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

    try:
        resource_dict = p.toolkit.get_action('resource_show')(context, {
            'id': res_id,
        })
    except logic.NotFound:
        return False

    datapusher_url = config.get('ckan.datapusher.url')

    callback_url_base = config.get('ckan.datapusher.callback_url_base')
    if callback_url_base:
        site_url = callback_url_base
        callback_url = urljoin(
            callback_url_base.rstrip('/'), '/api/3/action/datapusher_hook')
    else:
        site_url = h.url_for('/', qualified=True)
        callback_url = h.url_for(
            '/api/3/action/datapusher_hook', qualified=True)

    user = p.toolkit.get_action('user_show')(context, {'id': context['user']})

    for plugin in p.PluginImplementations(interfaces.IDataPusher):
        upload = plugin.can_upload(res_id)
        if not upload:
            msg = "Plugin {0} rejected resource {1}"\
                .format(plugin.__class__.__name__, res_id)
            log.info(msg)
            return False

    task = {
        'entity_id': res_id,
        'entity_type': 'resource',
        'task_type': 'datapusher',
        'last_updated': str(datetime.datetime.utcnow()),
        'state': 'submitting',
        'key': 'datapusher',
        'value': '{}',
        'error': '{}',
    }
    try:
        existing_task = p.toolkit.get_action('task_status_show')(context, {
            'entity_id': res_id,
            'task_type': 'datapusher',
            'key': 'datapusher'
        })
        assume_task_stale_after = datetime.timedelta(seconds=int(
            config.get('ckan.datapusher.assume_task_stale_after', 3600)))
        if existing_task.get('state') == 'pending':
            updated = datetime.datetime.strptime(
                existing_task['last_updated'], '%Y-%m-%dT%H:%M:%S.%f')
            time_since_last_updated = datetime.datetime.utcnow() - updated
            if time_since_last_updated > assume_task_stale_after:
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
    except logic.NotFound:
        pass

    context['ignore_auth'] = True
    p.toolkit.get_action('task_status_update')(context, task)

    site_user = p.toolkit.get_action(
        'get_site_user')({'ignore_auth': True}, {})

    try:
        r = requests.post(
            urljoin(datapusher_url, 'job'),
            headers={
                'Content-Type': 'application/json'
            },
            data=json.dumps({
                'api_key': site_user['apikey'],
                'job_type': 'push_to_datastore',
                'result_url': callback_url,
                'metadata': {
                    'ignore_hash': data_dict.get('ignore_hash', False),
                    'ckan_url': site_url,
                    'resource_id': res_id,
                    'set_url_type': data_dict.get('set_url_type', False),
                    'task_created': task['last_updated'],
                    'original_url': resource_dict.get('url'),
                }
            }))
        r.raise_for_status()
    except requests.exceptions.ConnectionError as e:
        error = {'message': 'Could not connect to DataPusher.',
                 'details': str(e)}
        task['error'] = json.dumps(error)
        task['state'] = 'error'
        task['last_updated'] = str(datetime.datetime.utcnow()),
        p.toolkit.get_action('task_status_update')(context, task)
        raise p.toolkit.ValidationError(error)

    except requests.exceptions.HTTPError as e:
        m = 'An Error occurred while sending the job: {0}'.format(str(e))
        try:
            body = e.response.json()
            if body.get('error'):
                m += ' ' + body['error']
        except ValueError:
            body = e.response.text
        error = {'message': m,
                 'details': body,
                 'status_code': r.status_code}
        task['error'] = json.dumps(error)
        task['state'] = 'error'
        task['last_updated'] = str(datetime.datetime.utcnow()),
        p.toolkit.get_action('task_status_update')(context, task)
        raise p.toolkit.ValidationError(error)

    value = json.dumps({'job_id': r.json()['job_id'],
                        'job_key': r.json()['job_key']})

    task['value'] = value
    task['state'] = 'pending'
    task['last_updated'] = str(datetime.datetime.utcnow()),
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
    task['last_updated'] = str(datetime.datetime.utcnow())

    resubmit = False

    if status == 'complete':
        # Create default views for resource if necessary (only the ones that
        # require data to be in the DataStore)
        resource_dict = p.toolkit.get_action('resource_show')(
            context, {'id': res_id})

        dataset_dict = p.toolkit.get_action('package_show')(
            context, {'id': resource_dict['package_id']})

        for plugin in p.PluginImplementations(interfaces.IDataPusher):
            plugin.after_upload(context, resource_dict, dataset_dict)

        logic.get_action('resource_create_default_resource_views')(
            context,
            {
                'resource': resource_dict,
                'package': dataset_dict,
                'create_datastore_views': True,
            })

        # Check if the uploaded file has been modified in the meantime
        if (resource_dict.get('last_modified') and
                metadata.get('task_created')):
            try:
                last_modified_datetime = parse_date(
                    resource_dict['last_modified'])
                task_created_datetime = parse_date(metadata['task_created'])
                if last_modified_datetime > task_created_datetime:
                    log.debug('Uploaded file more recent: {0} > {1}'.format(
                        last_modified_datetime, task_created_datetime))
                    resubmit = True
            except ValueError:
                pass
        # Check if the URL of the file has been modified in the meantime
        elif (resource_dict.get('url') and
                metadata.get('original_url') and
                resource_dict['url'] != metadata['original_url']):
            log.debug('URLs are different: {0} != {1}'.format(
                resource_dict['url'], metadata['original_url']))
            resubmit = True

    context['ignore_auth'] = True
    p.toolkit.get_action('task_status_update')(context, task)

    if resubmit:
        log.debug('Resource {0} has been modified, '
                  'resubmitting to DataPusher'.format(res_id))
        p.toolkit.get_action('datapusher_submit')(
            context, {'resource_id': res_id})


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

    datapusher_url = config.get('ckan.datapusher.url')
    if not datapusher_url:
        raise p.toolkit.ValidationError(
            {'configuration': ['ckan.datapusher.url not in config file']})

    value = json.loads(task['value'])
    job_key = value.get('job_key')
    job_id = value.get('job_id')
    url = None
    job_detail = None

    if job_id:
        url = urljoin(datapusher_url, 'job' + '/' + job_id)
        try:
            r = requests.get(url, headers={'Content-Type': 'application/json',
                                           'Authorization': job_key})
            r.raise_for_status()
            job_detail = r.json()
            for log in job_detail['logs']:
                if 'timestamp' in log:
                    date = time.strptime(
                        log['timestamp'], "%Y-%m-%dT%H:%M:%S.%f")
                    date = datetime.datetime.utcfromtimestamp(
                        time.mktime(date))
                    log['timestamp'] = date
        except (requests.exceptions.ConnectionError,
                requests.exceptions.HTTPError):
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
