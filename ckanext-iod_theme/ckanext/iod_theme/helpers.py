# -*- coding: utf-8 -

try:
    # CKAN 2.7 and later
    from ckan.common import config
except ImportError:
    # CKAN 2.6 and earlier
    from pylons import config

import logging
import ckan.logic as l
import ckan.model as m
from ckan.common import c
from ckan.authz import get_user_id_for_username



log = logging.getLogger(__name__)



def _get_context():
    return {
        'model': m,
        'session': m.Session,
        'user': c.user or c.author,
        'auth_user_obj': c.userobj
    }

def get_user_role_role_in_org(org_id):

    context = _get_context()
    user = context.get('user')
    user_id = get_user_id_for_username(user, allow_none=True)

    if not org_id:
        return None

    if not user_id:
        return None

    q = m.Session.query(m.Member) \
        .filter(m.Member.group_id == org_id) \
        .filter(m.Member.table_name == 'user') \
        .filter(m.Member.state == 'active') \
        .filter(m.Member.table_id == user_id)
    out = q.first()
    role = out.capacity
    return role


def _get_logic_functions(module_root, logic_functions={}):
    '''Helper function that scans extension logic dir for all logic functions.'''
    for module_name in ['create', 'update', 'patch']:
        module_path = '%s.%s' % (module_root, module_name,)

        module = __import__(module_path)

        for part in module_path.split('.')[1:]:
            module = getattr(module, part)

        for key, value in module.__dict__.items():
            if not key.startswith('_') and (hasattr(value, '__call__')
                                            and (value.__module__ == module_path)):
                logic_functions[key] = value

    return logic_functions