from copy import deepcopy
import re

from ckan.logic import NotFound
from ckan.lib.base import _, abort
import ckan.logic as logic
from ckan.plugins import PluginImplementations, ISubscription


def rename_keys(dict_, key_map, reverse=False, destructive=False):
    '''Returns a dict that has particular keys renamed,
    according to the key_map.

    Rename is by default non-destructive, so if the intended new
    key name already exists, it won\'t do that rename.

    To reverse the change, set reverse=True.'''
    new_dict = deepcopy(dict_)
    for key, mapping in key_map.items():
        if reverse:
            key, mapping = (mapping, key)
        if (not destructive) and new_dict.has_key(mapping):
            continue
        if dict_.has_key(key):
            value = dict_[key]
            new_dict[mapping] = value
            del new_dict[key]
    return new_dict

def get_domain_object(model, domain_object_ref):
    '''For an id or name, return the corresponding domain object.
    (First match returned, in order: system, package, group, auth_group, user).'''
    if domain_object_ref in ('system', 'System'):
        return model.System
    pkg = model.Package.get(domain_object_ref)
    if pkg:
        return pkg
    group = model.Group.get(domain_object_ref)
    if group:
        return group
    user = model.User.get(domain_object_ref)
    if user:
        return user
    raise NotFound('Domain object %r not found' % domain_object_ref)

def error_summary(error_dict):
    ''' Do some i18n stuff on the error_dict keys '''

    def prettify(field_name):
        field_name = re.sub('(?<!\w)[Uu]rl(?!\w)', 'URL',
                            field_name.replace('_', ' ').capitalize())
        return _(field_name.replace('_', ' '))

    summary = {}
    for key, error in error_dict.iteritems():
        if key == 'resources':
            summary[_('Resources')] = _('Package resource(s) invalid')
        elif key == 'extras':
            summary[_('Extras')] = _('Missing Value')
        elif key == 'extras_validation':
            summary[_('Extras')] = error[0]
        else:
            summary[_(prettify(key))] = error[0]
    return summary

        
def _get_subscription(context, data_dict):
    ''' Returns a subscription object by subscription_id or (user, subscription_name) or subscription_definition'''
    
    if 'user' not in context:
        raise logic.NotAuthorized
    model = context['model']
    user = model.User.get(context['user'])
    if not user:
        raise logic.NotAuthorized

    if 'subscription_id' in data_dict:
        subscription_id = logic.get_or_bust(data_dict, 'subscription_id')
        query = model.Session.query(model.Subscription)
        query = query.filter(model.Subscription.id==subscription_id)
        subscription = query.first()
        if subscription.owner_id != user.id:
            raise NotFound

    elif 'subscription_name' in data_dict:
        subscription_name = logic.get_or_bust(data_dict, 'subscription_name')
        query = model.Session.query(model.Subscription)
        query = query.filter(model.Subscription.owner_id==user.id)
        query = query.filter(model.Subscription.name==subscription_name)
        subscription = query.first() 
            
    elif 'subscription_definition' in data_dict:
        subscription_definition = logic.get_or_bust(data_dict, 'subscription_definition')
        query = model.Session.query(model.Subscription)
        query = query.filter(model.Subscription.owner_id==user.id)
        subscription = None
        for row in query.all():
            if _subscription_equal_definition(row, subscription_definition):
                subscription = row
                break
    else:
        raise NotFound

    if not subscription:
        raise NotFound 
            
    return subscription


def _subscription_equal_definition(subscription, definition):
    type_ = definition['type']
    data_type = definition['data_type']
        
    if type_ == 'search' and data_type == 'dataset':
        if subscription.definition['type'] != definition['type']:
            return False
            
        if subscription.definition['data_type'] != definition['data_type']:
            return False
            
        if subscription.definition['query'] != definition['query']:
            return False
            
        if set(subscription.definition['filters']) ^ set(definition['filters']):
            return False
            
        for filter_name, filter_value_list in subscription.definition['filters'].iteritems():
            if set(filter_value_list) ^ set(definition['filters'][filter_name]):
                return False
                    
        return True
    else:
        for plugin in PluginImplementations(ISubscription):
            if plugin.definition_type() == type_ and plugin.data_type() == data_type:
                return plugin.subscription_equal_definition(subscription, definition)

    return False

