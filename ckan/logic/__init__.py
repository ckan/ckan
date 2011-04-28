import logging
import ckan.authz

class ActionError(Exception):
    def __init__(self, extra_msg=None):
        self.extra_msg = extra_msg

class NotFound(ActionError):
    pass

class NotAuthorized(ActionError):
    pass

class ValidationError(ActionError):
    def __init__(self, error_dict, extra_msg=None):
        self.error_dict = error_dict
        self.extra_msg = extra_msg

log = logging.getLogger(__name__)

def clean_dict(data_dict):
    return dict((k, v) for k, v in data_dict.items() if v)

def tuplize_dict(data_dict):
    ''' gets a dict with keys of the form 'table__0__key' and converts them
    to a tuple like ('table', 0, 'key')'''

    tuplized_dict = {}
    for key, value in data_dict.iteritems():
        key_list = key.split('__')
        for num, key in enumerate(key_list):
            if num % 2 == 1:
                key_list[num] = int(key)
        tuplized_dict[tuple(key_list)] = value
    return tuplized_dict

def untuplize_dict(tuplized_dict):

    data_dict = {}
    for key, value in tuplized_dict.iteritems():
        new_key = '__'.join([str(item) for item in key])
        data_dict[new_key] = value
    return data_dict

def check_access(entity, action, context):
    model = context["model"]
    user = context.get("user")

    log.debug('check access - user %r' % user)
    
    if action and entity and not isinstance(entity, model.PackageRelationship):
        if action != model.Action.READ and user in (model.PSEUDO_USER__VISITOR, ''):
            log.debug("Valid API key needed to make changes")
            raise NotAuthorized
        
        am_authz = ckan.authz.Authorizer().is_authorized(user, action, entity)
        if not am_authz:
            log.debug("User is not authorized to %s %s" % (action, entity))
            raise NotAuthorized
    elif not user:
        log.debug("No valid API key provided.")
        raise NotAuthorized
    log.debug("Access OK.")
    return True                
