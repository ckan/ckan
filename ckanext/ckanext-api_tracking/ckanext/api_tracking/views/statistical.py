from typing import Any, Optional, cast
from urllib import request

from ckan.model import model
from ckan.types import Context
import ckan.logic as logic
from ckan.common import current_user, request

NotAuthorized= logic.NotAuthorized
ValidationError = logic.ValidationError
check_access = logic.check_access
get_action = logic.get_action

class CreateGroupView(MethodView):
    u'''Create statistical view '''
    
    def _prepare(self, data: Optional[dict[str, Any]] = None) -> Context:
        if data and u'type' in data:
            statistical_type = data['type']
        else:
            statistical_type = _guess_statistical_type()
        if data:
            data['type'] = statistical_type
        
        context = cast(Context, {
            u'model': model,
            u'session': model.Session,
            u'user': current_user.name,
            u'save': u'save' in request.args,
            u'parent': request.args.get(u'parent', None),
            u'statistical_type': statistical_type
        })    
            
        try:
            assert _check_access(u'group_create', context)
        except NotAuthorized:
            base.abort(403, _(u'Unauthorized to create a group'))

        return context    
            
            
            
            
            
            
            
            
            
            
            
            
def _guess_statistical_type(expecting_name: bool = False) -> str:
    u"""
            Guess the type of stati from the URL.
            * The default url '/stati/xyz' returns None
            * stati_type is unicode
            * this handles the case where there is a prefix on the URL
              (such as /data/organization)
        """
    parts: list[str] = request.path.split(u'/')
    parts = [x for x in parts if x]

    idx = 0
    if expecting_name:
        idx = -1

    gt = parts[idx]

    return gt

def _check_access(action_name: str, *args: Any, **kw: Any) -> Literal[True]:
    u''' select the correct group/org check_access '''
    return check_access(_replace_group_org(action_name), *args, **kw)
