from ckan.tests import *
import ckan.model as model

class TestAccountController(TestController2):

    def test_account(self):
        offset = url_for(controller='account')
        res = self.app.get(offset)
        assert 'Account - Home' in res
        assert 'CKAN uses' in res
        assert 'Getting an OpenID' in res

    def test_account_login(self):
        offset = url_for(controller='account', action='login')
        res = self.app.get(offset, status=401)
        assert 'Please login now' in res
        # cannot use with AuthKit 0.4.0 (see below)
        # res = self._login_form(res)
        # neither does this plus it is slow as it is external
        # self._login_openid(res)
        # assert 'You are now logged in as' in res

    def _login_form(self, res):
        # cannot use for time being due to 'bug' in AuthKit
        # paste.fixture does not set REMOTE_ADDR which AuthKit requires to do
        # its stuff (though note comment in code suggesting amendment)
        # create cookie see authkit/authenticate/cookie.py l. 364 
            # if self.include_ip:
            # # Fixes ticket #30
            # # @@@ should this use environ.get('REMOTE_ADDR','0.0.0.0')?
            #  remote_addr = environ.get('HTTP_X_FORWARDED_FOR', environ['REMOTE_ADDR'])
            #  
            # KeyError: 'REMOTE_ADDR' 
        # could get round this by adding stuff to environ using paste fixture's
        # extra_environ, see:
        # http://pythonpaste.org/webtest/#modifying-the-environment-simulating-authentication
        assert 'Please Sign In' in res
        username = 'okfntest'
        password = 'okfntest'
        fv = res.forms[0]
        fv['username'] = username
        fv['password'] = password
        res = fv.submit()
        return res

    def _login_openid(self, res):
        # this requires a valid account on some openid provider
        # (or for us to stub an open_id provider ...)
        assert 'Please Sign In' in res
        username = 'http://okfntest.myopenid.com'
        fv = res.forms[0]
        fv['passurl'] =  username
        web.submit()
        web.code(200)
        assert 'You must sign in to authenticate to' in res
        assert username in res
        fv['password'] =  'okfntest'
        res = fv.submit()
        print str(res)
        assert 'Please carefully verify whether you wish to trust' in res
        fv = res.forms[0]
        res = fv.submit('allow_once')
        # at this point we should return
        # but for some reason this does not work ...
        return res

    def test_logout(self):
        offset = url_for(controller='account', action='logout')
        res = self.app.get(offset)
        assert 'You have logged out successfully.' in res

    # -----------
    # tests for top links present in every page

    def test_home_register(self):
        offset = url_for(controller='home')
        res = self.app.get(offset)
        res = res.click('Register', index=0)
        print str(res)
        assert 'Account - Home' in res

    def test_home_login(self):
        offset = url_for(controller='home')
        res = self.app.get(offset)
        # cannot use click because it does not allow a 401 response ...
        # could get round this by checking that url is correct and then doing a
        # get but then we are back to test_account_login
        # res = res.click('Login', index=0)
        # assert 'Please Sign In' in res

     # TODO: test sign in results in:
     # a) a username at top of page
     # b) logout link

    def test_apikey(self):
        # not_logged_in
        key = model.ApiKey.by_name('okfntest')
        if key:
            key.purge()

        offset = url_for(controller='account', action='apikey')
        res = self.app.get(offset, status=[401]) 

        res = self.app.get(offset, extra_environ=dict(REMOTE_USER='okfntest'))
        key = model.ApiKey.byName('okfntest')
        assert 'Your API key is: %s' % key.key in res, res

        # run again to check case where ApiKey already exists
        res = self.app.get(offset, extra_environ=dict(REMOTE_USER='okfntest'))
        key = model.ApiKey.byName('okfntest')
        assert 'Your API key is: %s' % key.key in res, res
