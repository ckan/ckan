import ckan.plugins.toolkit as toolkit
from ckanext.xloader.utils import XLoaderFormats
from markupsafe import Markup
from html import escape as html_escape


def xloader_status(resource_id):
    try:
        return toolkit.get_action('xloader_status')(
            {}, {'resource_id': resource_id})
    except toolkit.ObjectNotFound:
        return {
            'status': 'unknown'
        }


def xloader_status_description(status):
    _ = toolkit._

    if status.get('status'):
        captions = {
            'complete': _('Complete'),
            'pending': _('Pending'),
            'submitting': _('Submitting'),
            'error': _('Error'),
        }

        return captions.get(status['status'], status['status'].capitalize())
    else:
        return _('Not Uploaded Yet')


def is_resource_supported_by_xloader(res_dict, check_access=True):
    is_supported_format = XLoaderFormats.is_it_an_xloader_format(res_dict.get('format'))
    is_datastore_active = res_dict.get('datastore_active', False)
    user_has_access = not check_access or toolkit.h.check_access(
        'package_update', {'id': res_dict.get('package_id')})
    url_type = res_dict.get('url_type')
    if url_type:
        try:
            is_supported_url_type = url_type not in toolkit.h.datastore_rw_resource_url_types()
        except AttributeError:
            is_supported_url_type = (url_type == 'upload')
    else:
        is_supported_url_type = True
    return (is_supported_format or is_datastore_active) and user_has_access and is_supported_url_type


def xloader_badge(resource):
    # type: (dict) -> str
    """
    Displays a custom badge for the status of Xloader and DataStore for the specified resource.
    """
    if not toolkit.asbool(toolkit.config.get('ckanext.xloader.show_badges', True)):
        return ''

    if not XLoaderFormats.is_it_an_xloader_format(resource.get('format')):
        # we only want to show badges for supported xloader formats
        return ''

    is_datastore_active = resource.get('datastore_active', False)

    try:
        xloader_job = toolkit.get_action("xloader_status")({'ignore_auth': True},
                                                           {"resource_id": resource.get('id')})
    except toolkit.ObjectNotFound:
        xloader_job = {}

    if xloader_job.get('status') == 'complete':
        # the xloader task is complete, show datastore active or inactive.
        # xloader will delete the datastore table at the beggining of the job run.
        # so this will only be true if the job is fully finished.
        status = 'active' if is_datastore_active else 'inactive'
    elif xloader_job.get('status') in ['submitting', 'pending', 'running', 'running_but_viewable', 'error']:
        # the job is running or pending or errored
        # show the xloader status
        status = xloader_job.get('status')
        if status == 'running_but_viewable':
            # treat running_but_viewable the same as running
            status = 'running'
        elif status == 'submitting':
            # treat submitting the same as pending
            status = 'pending'
    else:
        # we do not know what the status is
        status = 'unknown'

    status_translations = {
        # Default messages
        'pending': toolkit._('Pending'),
        'running': toolkit._('Running'),
        'error': toolkit._('Error'),
        # Debug messages
        'complete': toolkit._('Complete'),
        'active': toolkit._('Active'),
        'inactive': toolkit._('Inactive'),
        'unknown': toolkit._('Unknown'),
    }

    status_descriptions = {
        # Default messages
        'pending': toolkit._('Data awaiting load to DataStore'),
        'running': toolkit._('Loading data into DataStore'),
        'error': toolkit._('Failed to load data into DataStore'),
        # Debug messages
        'complete': toolkit._('Data loaded into DataStore'),
        'active': toolkit._('Data available in DataStore'),
        'inactive': toolkit._('Resource not active in DataStore'),
        'unknown': toolkit._('DataStore status unknown'),
    }
    basic_statuses = ['pending', 'running', 'error']

    if status not in basic_statuses and not toolkit.asbool(toolkit.config.get('ckanext.xloader.debug_badges', False)):
        return ''

    last_updated = toolkit.h.render_datetime(xloader_job.get('last_updated'), with_hours=True) \
        if xloader_job.get('last_updated') else toolkit._('Last Updated Not Available')

    try:
        toolkit.check_access('resource_update', {'user': toolkit.g.user}, {'id': resource.get('id')})
        pusher_url = toolkit.h.url_for('xloader.resource_data',
                                       id=resource.get('package_id'),
                                       resource_id=resource.get('id'))

        return Markup(u'''
    <a href="{pusher_url}" class="loader-badge" title="{title}: {status_description}" >
        <span class="prefix">{prefix}</span>
        <span class="status {status}">{status_display}</span>
    </a>'''.format(
            pusher_url=pusher_url,
            prefix=toolkit._('datastore'),
            status=status,
            status_display=html_escape(status_translations[status], quote=True),
            status_description=html_escape(status_descriptions[status], quote=True),
            title=html_escape(last_updated, quote=True)))
    except toolkit.NotAuthorized:
        return Markup(u'''
    <span class="loader-badge" title="{title}: {status_description}">
        <span class="prefix">{prefix}</span>
        <span class="status {status}">{status_display}</span>
    </span>
    '''.format(
            prefix=toolkit._('datastore'),
            status=status,
            status_display=html_escape(status_translations[status], quote=True),
            status_description=html_escape(status_descriptions[status], quote=True),
            title=html_escape(last_updated, quote=True)))
