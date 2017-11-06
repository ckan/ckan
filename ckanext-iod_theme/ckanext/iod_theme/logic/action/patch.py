# -*- coding: utf-8 -
import logging
import ckan.logic as l
import ckanext.iod_theme.helpers as h

_check_access = l.check_access

log = logging.getLogger(__name__)

def package_patch(context, data_dict):
    _check_access('has_user_permission_to_make_dataset_public', context, data_dict)

    if data_dict and 'geographic_string' in data_dict.keys():
        h.convert_to_tags('geographic_string', data_dict, context, 'geographic_strings')

    return l.action.patch.package_patch(context, data_dict)