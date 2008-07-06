from ckan.lib.base import *
from ckan.controllers.base import CkanBaseController
import sqlobject 

def login_form():
    return render('account/login_form').replace('FORM_ACTION', '%s')

# Todo: Make AuthKit work with the Genshi template.
openid_form_template = """\
<html>
  <head><title>Please Sign In</title></head>
  <body>
    <h1>Please Sign In</h1>
    <div class="$css_class">$message</div>
    <form action="$action" method="post">
      <dl>
        <dt>Pass url:</dt>
        <dd><input type="text" name="passurl" value="$value"></dd>
      </dl>
      <input type="submit" name="authform" />
      <hr />
    </form>
  </body>
</html>
"""

def openid_form():
    return openid_form_template
 
class AccountController(CkanBaseController):

    def index(self):
        c.login_page = h.url_for(controller='account', action='login')
        return render('account/index')

    def login_form(self, return_url=''):
        return render('account/login_form')

    def openid_form(self, return_url=''):
        return render('account/openid_form').replace('DOLAR', '$')

    def login(self, return_url=''):
        if request.environ.has_key('REMOTE_USER'):
            c.user = request.environ['REMOTE_USER']
            return render('account/logged_in')
        else:
            abort(401)

    def logout(self):
        c.user = None
        return render('account/logout')

    def apikey(self):
        # logged in
        if not c.user:
            abort(401)
        else:
            try:
                apikey_object = model.ApiKey.byName(c.user)
            except sqlobject.SQLObjectNotFound:
                apikey_object = model.ApiKey(name=c.user)
            c.api_key = apikey_object.key
        return render('account/apikey')

