# -*- coding: utf-8 -
import logging
import ckan.logic as l

_check_access = l.check_access

log = logging.getLogger(__name__)

def package_patch(context, data_dict):
    _check_access('has_user_permission_to_make_dataset_public', context, data_dict)
    return l.action.patch.package_patch(context, data_dict)