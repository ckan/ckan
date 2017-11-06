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
import ckan.plugins.toolkit as tk
import ckan.model as model
import ckan.lib.navl.dictization_functions as df
import ckan.logic.validators as validators

from ckan.common import c
from ckan.authz import get_user_id_for_username
from ckan.common import _


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


def _create_vocabulary(vocab_name, tag_list):
    user = tk.get_action('get_site_user')({'ignore_auth': True}, {})
    context = {'user': user['name']}
    try:
        data = {'id': vocab_name}
        tk.get_action('vocabulary_show')(context, data)
    except tk.ObjectNotFound:
        data = {'name': vocab_name}
        vocab = tk.get_action('vocabulary_create')(context, data)
        for tag in tag_list:
            data = {'name': tag, 'vocabulary_id': vocab['id']}
            tk.get_action('tag_create')(context, data)
    try:
        tags = tk.get_action('tag_list')(data_dict={'vocabulary_id': vocab_name})
        return tags
    except tk.ObjectNotFound:
        return None


def create_geographic_strings():
    tags = _create_vocabulary('geographic_strings', ['National', 'Province', 'County', 'District', 'Rural district', 'City', 'Village'])
    return tags


def convert_to_tags(key, data, context, vocab):
    new_tags = data[key]
    if not new_tags:
        return
    if isinstance(new_tags, basestring):
        new_tags = [new_tags]

    v = model.Vocabulary.get(vocab)
    if not v:
        raise df.Invalid(_('Tag vocabulary "%s" does not exist') % vocab)
    context['vocabulary'] = v

    for tag in new_tags:
        validators.tag_in_vocabulary_validator(tag, context)

    for num, tag in enumerate(new_tags):
        if  not data['tags']:
            data['tags'] = []

        data['tags'].append({'name': tag,
                             'vocabulary_id': v.id,
                             'state': 'active'})

    return data


def free_tags_only(tags):
    free_tags = []
    for tag in tags:
        if tag['vocabulary_id']:
            continue
        free_tags.append(tag)
    return free_tags