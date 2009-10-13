import logging
from ckan.lib.base import BaseController, render, abort
from ckan import model
from ckan import forms
from ckan.model import meta
import ckan.authz
from formalchemy.ext.pylons.admin import FormAlchemyAdminController

log = logging.getLogger(__name__)

class AdminController(BaseController):
    model = model # where your SQLAlchemy mappers are
    forms = forms # module containing FormAlchemy fieldsets definitions
    def Session(self): # Session factory
        return meta.Session

    def __before__(self, action, **params):
        # note c.user is not available, so use environ
        username = params['environ'].get('REMOTE_USER', '')
        if not ckan.authz.Authorizer().is_sysadmin(unicode(username)):
            abort(401, 'Need to be system administrator to administer')        


AdminController = FormAlchemyAdminController(AdminController)
