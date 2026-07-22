# encoding: utf-8
from __future__ import annotations

from typing import Any, Optional
import ckan.plugins.toolkit as toolkit


def datapusher_status(resource_id: str):
    try:
        return toolkit.get_action('datapusher_status')(
            {}, {'resource_id': resource_id})
    except toolkit.ObjectNotFound:
        return {
            'status': 'unknown'
        }


def datapusher_status_description(status: dict[str, Any]):
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


def is_resource_supported_by_datapusher(res_dict: dict[str, Any],
                                        check_access: Optional[bool] = True):
    supported_formats = toolkit.config.get('ckan.datapusher.formats')
    is_supported_format = res_dict.get('format', u'').lower() \
        in supported_formats
    is_datastore_active = res_dict.get('datastore_active', False)
    if check_access:
        user_has_access = toolkit.h.check_access(
            'package_update', {'id': res_dict.get('package_id')})
    else:
        user_has_access = True
    is_supported_url_type = res_dict.get('url_type') \
        not in toolkit.h.datastore_rw_resource_url_types()
    return (is_supported_format or is_datastore_active) \
        and user_has_access and is_supported_url_type
