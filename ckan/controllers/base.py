from ckan.lib.base import *

class CkanBaseController(BaseController):

    def __before__(self, action, **params):
        # what is different between session['user'] and environ['REMOTE_USER']
        c.user = request.environ.get('REMOTE_USER', None)
        c.remote_addr = request.environ.get('REMOTE_ADDR', 'Unknown IP Address')
        if c.user:
            c.author = c.user
        else:
            c.author = c.remote_addr

