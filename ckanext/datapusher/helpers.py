# encoding: utf-8
from __future__ import annotations

from typing import Any
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
