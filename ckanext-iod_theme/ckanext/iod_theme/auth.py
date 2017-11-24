import ckan.plugins as p

try:
    import ckan.authz as authz
except ImportError:
    import ckan.new_authz as authz

import db


def sysadmin(context, data_dict):
    return {'success':  False}

def anyone(context, data_dict):
    return {'success': True}


# Starting from 2.2 you need to explicitly flag auth functions that allow
# anonymous access
if p.toolkit.check_ckan_version(min_version='2.2'):
    anyone = p.toolkit.auth_allow_anonymous_access(anyone)


def group_admin(context, data_dict):
    return p.toolkit.check_access('group_update', context, data_dict)


def org_admin(context, data_dict):
    return p.toolkit.check_access('group_update', context, data_dict)


def page_privacy(context, data_dict):
    if db.pages_table is None:
        db.init_db(context['model'])
    org_id = data_dict.get('org_id')
    page = data_dict.get('page')
    out = db.Page.get(group_id=org_id, name=page)
    if out and out.private == False:
        return {'success':  True}
    # no org_id means it's a universal page
    if not org_id:
        if out and out.private:
            return {'success': False}
        return {'success': True}
    group = context['model'].Group.get(org_id)
    user = context['user']
    authorized = authz.has_user_permission_for_group_or_org(group.id,
                                                                user,
                                                                'read')
    if not authorized:
        return {'success': False,
                'msg': p.toolkit._(
                    'User %s not authorized to read this page') % user}
    else:
        return {'success': True}


# Starting from 2.2 you need to explicitly flag auth functions that allow
# anonymous access
if p.toolkit.check_ckan_version(min_version='2.2'):
    anyone = p.toolkit.auth_allow_anonymous_access(anyone)
    page_privacy = p.toolkit.auth_allow_anonymous_access(page_privacy)


pages_show = page_privacy
pages_update = org_admin
pages_delete = org_admin
pages_list = anyone
pages_upload = sysadmin
org_pages_show = page_privacy
org_pages_update = org_admin
org_pages_delete = org_admin
org_pages_list = anyone
group_pages_show = page_privacy
group_pages_update = group_admin
group_pages_delete = group_admin
group_pages_list = anyone