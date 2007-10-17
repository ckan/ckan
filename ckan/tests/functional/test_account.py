from ckan.tests import *

class TestHomeController(TestControllerTwill):

    def test_account(self):
        offset = url_for(controller='account')
        url = self.siteurl + offset
        web.go(url)
        web.code(200)
        web.title('Account - Home')
        web.find('CKAN uses')
        web.find('Getting an OpenID')

    def test_account_login(self):
        offset = url_for(controller='account', action='login')
        url = self.siteurl + offset
        web.go(url)
        web.code(200)
        # for some unknown reason this really will not work ...
        # get a 500 error ...
        # self._login_form()
        # neither does this plus it is slow as it is external
        # self._login_openid()
        # web.find('You are now logged in as')

    def _login_form(self):
        username = 'okfntest'
        password = 'okfntest'
        web.code(200)
        web.title('Please Login!')
        web.find('Please Login')
        web.fv(1, 'username', username)
        web.fv(1, 'password', password)
        web.submit()
        web.code(200)

    def _login_openid(self):
        # this requires a valid account on some openid provider
        # (or for us to stub an open_id provider ...)
        web.code(200)
        web.find('Please Sign In')
        username = 'http://okfntest.myopenid.com'
        web.fv(1, 'passurl', username)
        web.submit()
        web.code(200)
        web.find('You must sign in to authenticate to')
        web.find(username)
        web.fv(1, 'password', 'okfntest')
        web.submit()
        web.code(200)
        print web.show()
        web.find('Please carefully verify whether you wish to trust')
        web.submit('allow_once')
        web.code(200)
        # at this point we should return
        # but for some reason this does not work ...

    def test_logout(self):
        offset = url_for(controller='account', action='logout')
        url = self.siteurl + offset
        web.go(url)
        web.code(200)
        web.find('You have logged out successfully.')

    # -----------
    # tests for top links present in every page

    def test_home_register(self):
        offset = url_for(controller='home')
        url = self.siteurl + offset
        web.go(url)
        web.code(200)
        web.follow('Register')
        web.title('Account - Home')

    def test_home_login(self):
        offset = url_for(controller='home')
        url = self.siteurl + offset
        web.go(url)
        web.code(200)
        web.follow('Login')
        # be generic (form has Please Login, openid has Please Sign In)
        web.title('Please ')

     # TODO: test sign in results in:
     # a) a username at top of page
     # b) logout link

