# encoding: utf-8

import ckan.logic as logic
import ckan.authz as authz

import ckan.logic.auth as logic_auth
from ckan.common import _

import ckanext.iod_theme.helpers as h



@logic.auth_allow_anonymous_access
def has_user_permission_to_make_dataset_public(context, data_dict):

    user = context.get('user')
    package_id = data_dict['id']
    package = logic.get_action('package_show')(context,
                                           {'id': package_id})

    if 'owner_org' in package.keys() and 'private' in data_dict.keys():

        role = h.get_user_role_role_in_org(package['owner_org'])

        if role == 'editor' and str(package['private']) != str(data_dict['private']):

            return {'success': False,
                    'msg': _('User %s not authorized to make package %s public') %
                           (str(user), data_dict['id'])}


    return {'success': True}
