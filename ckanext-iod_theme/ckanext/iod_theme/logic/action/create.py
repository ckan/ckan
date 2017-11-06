# -*- coding: utf-8 -
import logging
import ckan.logic as l
import ckanext.iod_theme.helpers as h

log = logging.getLogger(__name__)


def package_create(context, data_dict):
    org_id = data_dict['owner_org']
    role = h.get_user_role_role_in_org(org_id)

    # If the user is editor make sure the new created
    # dataset is always be private
    if role and role == 'editor':
        data_dict['private'] = True

    if data_dict and 'geographic_string' in data_dict.keys():
        h.convert_to_tags('geographic_string', data_dict, context, 'geographic_strings')

    return l.action.create.package_create(context, data_dict)