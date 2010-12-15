import logging
from ckan.lib.base import BaseController, render, abort
from ckan import model
from ckan import forms
from ckan.model import meta
import ckan.authz
from formalchemy.ext.pylons.controller import ModelsController

log = logging.getLogger(__name__)

class AdminControllerBase(BaseController):
    model = model # where your SQLAlchemy mappers are
    forms = forms # module containing FormAlchemy fieldsets definitions
    def Session(self): # Session factory
        return meta.Session

    def __before__(self, action, **params):
        self._start_call_timing()
        # note c.user is not available, so use environ
        username = params['environ'].get('REMOTE_USER', '')
        if not ckan.authz.Authorizer().is_sysadmin(unicode(username)):
            abort(401, 'Need to be system administrator to administer')        


AdminController = ModelsController(AdminControllerBase,
                                   prefix_name='admin',
                                   member_name='model',
                                   collection_name='models',
                                   )
