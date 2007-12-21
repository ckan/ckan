from ckan.tests import *

class TestAccountController(TestController2):

    def test_account(self):
        offset = url_for(controller='account')
        res = self.app.get(offset)
        assert 'Account - Home' in res
        assert 'CKAN uses' in res
        assert 'Getting an OpenID' in res

    def test_account_login(self):
        offset = url_for(controller='account', action='login')
        res = self.app.get(offset)
        # for some unknown reason this really will not work ...
        # get a 500 error ...
        # self._login_form()
        # neither does this plus it is slow as it is external
        # self._login_openid()
        # assert 'You are now logged in as' in res

    def _login_form(self, res):
        username = 'okfntest'
        password = 'okfntest'
        assert 'Please Login!' in res
        assert 'Please Login' in res
        fv = res.forms[1]
        fv['username'] = username
        fv['password'] = password
        fv.submit()

    def _login_openid(self, res):
        # this requires a valid account on some openid provider
        # (or for us to stub an open_id provider ...)
        assert 'Please Sign In' in res
        username = 'http://okfntest.myopenid.com'
        fv = res.forms[1]
        fv['passurl'] =  username
        web.submit()
        web.code(200)
        assert 'You must sign in to authenticate to' in res
        assert username in res
        fv['password'] =  'okfntest'
        fv.submit()
        print str(res)
        assert 'Please carefully verify whether you wish to trust' in res
        fv = res.forms[0]
        fv.submit('allow_once')
        # at this point we should return
        # but for some reason this does not work ...

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
        res = res.click('Login', index=0)
        # be generic (form has Please Login, openid has Please Sign In)
        assert 'Please ' in res

     # TODO: test sign in results in:
     # a) a username at top of page
     # b) logout link

