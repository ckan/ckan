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
