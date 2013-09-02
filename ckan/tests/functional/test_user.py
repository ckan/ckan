from routes import url_for
from nose.tools import assert_equal
from pylons import config
import hashlib

from ckan.tests import search_related, CreateTestData
from ckan.tests.html_check import HtmlCheckMethods
from ckan.tests.pylons_controller import PylonsTestCase
from ckan.tests.mock_mail_server import SmtpServerHarness
import ckan.model as model
from base import FunctionalTestCase
from ckan.lib.mailer import get_reset_link, create_reset_key

class TestUserController(FunctionalTestCase, HtmlCheckMethods, PylonsTestCase, SmtpServerHarness):
    @classmethod
    def setup_class(cls):
        smtp_server = config.get('smtp.test_server')
        if smtp_server:
            host, port = smtp_server.split(':')
            port = int(port) + int(str(hashlib.md5(cls.__name__).hexdigest())[0], 16)
            config['smtp.test_server'] = '%s:%s' % (host, port)

        PylonsTestCase.setup_class()
        SmtpServerHarness.setup_class()
        CreateTestData.create()

        # make 3 changes, authored by annafan
        for i in range(3):
            rev = model.repo.new_revision()
            pkg = model.Package.by_name(u'annakarenina')
            pkg.notes = u'Changed notes %i' % i
            rev.author = u'annafan'
            model.repo.commit_and_remove()

        CreateTestData.create_user('unfinisher', about='<a href="http://unfinished.tag')
        CreateTestData.create_user('uncloser', about='<a href="http://unclosed.tag">')
        CreateTestData.create_user('spammer', about=u'<a href="http://mysite">mysite</a> <a href=\u201dhttp://test2\u201d>test2</a>')
        CreateTestData.create_user('spammer2', about=u'<a href="http://spamsite1.com\u201d>spamsite1</a>\r\n<a href="http://www.spamsite2.com\u201d>spamsite2</a>\r\n')

    @classmethod
    def teardown_class(self):
        # clear routes 'id' so that next test to run doesn't get it
        self.app.get(url_for(controller='user', action='login', id=None))
        SmtpServerHarness.teardown_class()
        model.repo.rebuild_db()

    def teardown(self):
        # just ensure we're not logged in
        self.app.get('/user/logout')

    def test_user_read(self):
        user = model.User.by_name(u'annafan')
        offset = '/user/%s' % user.id
        res = self.app.get(offset, status=200)
        main_res = self.main_div(res)
        assert 'annafan' in res, res
        assert 'Logged in' not in main_res, main_res
        assert 'checkpoint:is-myself' not in main_res, main_res
        assert 'about' in main_res, main_res
        assert 'I love reading Annakarenina' in res, main_res
        self.check_named_element(res, 'a',
                                 'http://anna.com',
                                 'target="_blank"',
                                 'rel="nofollow"')
        assert 'Edit Profile' not in main_res, main_res

    def test_user_read_without_id(self):
        offset = '/user/'
        res = self.app.get(offset, status=302)

    def test_user_read_me_without_id(self):
        offset = '/user/me'
        res = self.app.get(offset, status=302)

    def test_user_read_without_id_but_logged_in(self):
        user = model.User.by_name(u'annafan')
        offset = '/user/annafan'
        res = self.app.get(offset, status=200, extra_environ={'REMOTE_USER': str(user.name)})
        main_res = self.main_div(res)
        assert 'annafan' in main_res, main_res
        assert 'checkpoint:is-myself' in main_res, main_res

    def test_user_read_logged_in(self):
        user = model.User.by_name(u'annafan')
        offset = '/user/%s' % user.id
        res = self.app.get(offset, extra_environ={'REMOTE_USER': str(user.name)})
        main_res = self.main_div(res)
        assert 'annafan' in res, res
        assert 'checkpoint:is-myself' in main_res, main_res
        assert 'Edit Profile' in main_res, main_res


    def test_user_login_page(self):
        offset = url_for(controller='user', action='login', id=None)
        res = self.app.get(offset, status=200)
        assert 'Login' in res, res
        assert 'Please click your account provider' in res, res
        assert 'Forgot your password?' in res, res
        assert 'Don\'t have an OpenID' in res, res

    def test_logout(self):
        res = self.app.get('/user/_logout')
        res2 = res.follow()
        while res2.status == 302:
            res2 = res2.follow()
        assert 'You have logged out successfully.' in res2, res2

    def _get_cookie_headers(self, res):
        # For a request response, returns the Set-Cookie header values.
        cookie_headers = []
        for key, value in res.headers:
            if key == 'Set-Cookie':
                cookie_headers.append(value)
        return cookie_headers

    def test_login(self):
        # create test user
        username = u'testlogin'
        password = u'letmein'
        CreateTestData.create_user(name=username,
                                   password=password)
        user = model.User.by_name(username)

        # do the login
        offset = url_for(controller='user', action='login')
        res = self.app.get(offset)
        fv = res.forms['login']
        fv['login'] = str(username)
        fv['password'] = str(password)
        fv['remember'] = False
        res = fv.submit()

        # check cookies set
        cookies = self._get_cookie_headers(res)
        assert cookies
        for cookie in cookies:
            assert not 'max-age' in cookie.lower(), cookie

        # first get redirected to user/logged_in
        assert_equal(res.status, 302)
        assert res.header('Location').startswith('http://localhost/user/logged_in') or \
               res.header('Location').startswith('/user/logged_in')

        # then get redirected to user's dashboard
        res = res.follow()
        res = res.follow()
        assert_equal(res.status, 302)
        assert res.header('Location').startswith('http://localhost/dashboard') or \
               res.header('Location').startswith('/dashboard')
        res = res.follow()
        assert_equal(res.status, 200)
        assert 'testlogin is now logged in' in res.body
        assert 'checkpoint:my-dashboard' in res.body

        # check user object created
        user = model.User.by_name(username)
        assert user
        assert_equal(user.name, username)
        assert len(user.apikey) == 36

        # check cookie created
        cookie = res.request.environ['HTTP_COOKIE']
        assert 'auth_tkt=' in cookie, cookie
        assert 'testlogin!userid_type:unicode' in cookie, cookie

        # navigate to another page and check username still displayed
        res = res.click('Search')
        assert 'testlogin' in res.body, res.body

    def test_login_remembered(self):
        # create test user
        username = u'testlogin2'
        password = u'letmein'
        CreateTestData.create_user(name=username,
                                   password=password)
        user = model.User.by_name(username)

        # do the login
        offset = url_for(controller='user', action='login')
        res = self.app.get(offset)
        fv = res.forms['login']
        fv['login'] = str(username)
        fv['password'] = str(password)
        fv['remember'] = True
        res = fv.submit()

        # check cookies set
        cookies = self._get_cookie_headers(res)
        assert cookies
        # check cookie is remembered via Max-Age and Expires
        # (both needed for cross-browser compatibility)
        for cookie in cookies:
            assert 'Max-Age=63072000;' in cookie, cookie
            assert 'Expires=' in cookie, cookie

    def test_login_wrong_password(self):
        # create test user
        username = u'testloginwrong'
        password = u'letmein'
        CreateTestData.create_user(name=username,
                                   password=password)
        user = model.User.by_name(username)

        # do the login
        offset = url_for(controller='user', action='login')
        res = self.app.get(offset)
        fv = res.forms['login']
        fv['login'] = username
        fv['password'] = 'wrong_password'
        res = fv.submit()

        # first get redirected to logged_in
        assert_equal(res.status, 302)
        assert res.header('Location').startswith('http://localhost/user/logged_in') or \
               res.header('Location').startswith('/user/logged_in')

        # then get redirected to login
        res = res.follow()
        res = res.follow()
        assert_equal(res.status, 302)
        assert res.header('Location').startswith('http://localhost/user/login') or \
               res.header('Location').startswith('/user/login')
        res = res.follow()
        assert_equal(res.status, 200)
        assert 'Login failed. Bad username or password.' in res.body
        assert 'Login:' in res.body

    def test_relogin(self):
        '''Login as user A and then (try to) login as user B (without
        logout). #1799.'''
        # create test users A & B
        password = u'letmein'
        CreateTestData.create_user(name=u'user_a',
                                   password=password)
        CreateTestData.create_user(name=u'user_b',
                                   password=password)
        userA = model.User.by_name(u'user_a')
        userB = model.User.by_name(u'user_b')

        # do the login
        offset = url_for(controller='user', action='login')
        res = self.app.get(offset)
        fv = res.forms['login']
        fv['login'] = 'user_a'
        fv['password'] = str(password)
        res = fv.submit()
        while res.status == 302:
            res = res.follow()
        assert_equal(res.status, 200)

        # login as userB
        offset = url_for(controller='user', action='login')
        res = self.app.get(offset)
        assert not res.forms.has_key('login') # i.e. no login box is presented
        assert 'To register or log in as another user' in res.body, res.body
        assert 'logout' in res.body, res.body

        # Test code left commented - shows the problem if you
        # let people try to login whilst still logged in. #1799
##        fv['login'] = 'user_b'
##        fv['password'] = str(password)
##        res = fv.submit()
##        while res.status == 302:
##            res = res.follow()
##        assert_equal(res.status, 200)

##        offset = url_for(controller='user', action='me')
##        res = self.app.get(offset)
##        assert_equal(res.status, 302)
##        res = res.follow()
##        assert 'user_b' in res

    def test_try_to_register_whilst_logged_in(self):
        '''Login as user A and then (try to) register user B (without
        logout). #1799.'''
        # create user A
        password = u'letmein'
        CreateTestData.create_user(name=u'user_a_',
                                   password=password)
        userA = model.User.by_name(u'user_a_')

        # do the login
        offset = url_for(controller='user', action='login')
        res = self.app.get(offset)
        fv = res.forms['login']
        fv['login'] = 'user_a_'
        fv['password'] = str(password)
        res = fv.submit()
        while res.status == 302:
            res = res.follow()
        assert_equal(res.status, 200)

        # try to register
        offset = url_for(controller='user', action='register')
        res = self.app.get(offset)
        assert not res.forms.has_key('Password') # i.e. no registration form
        assert 'To register or log in as another user' in res.body, res.body
        assert 'logout' in res.body, res.body

    def test_register_whilst_logged_in(self):
        '''Start registration form as user B then in another window login
        as user A, and then try and then submit form for user B. #1799.'''
        # create user A
        password = u'letmein'
        CreateTestData.create_user(name=u'user_a__',
                                   password=password)
        userA = model.User.by_name(u'user_a__')
        # make him a sysadmin, to ensure he is allowed to create a user
        model.add_user_to_role(userA, model.Role.ADMIN, model.System())
        model.repo.commit_and_remove()
        userA = model.User.by_name(u'user_a__')

        # start to register user B
        offset = url_for(controller='user', action='register')
        res = self.app.get(offset)
        fvA = res.forms['user-edit']
        fvA['name'] = 'user_b_'
        fvA['fullname'] = 'User B'
        fvA['email'] = 'user@b.com'
        fvA['password1'] = password
        fvA['password2'] = password

        # login user A
        offset = url_for(controller='user', action='login')
        res = self.app.get(offset)
        fvB = res.forms['login']
        fvB['login'] = 'user_a__'
        fvB['password'] = str(password)
        res = fvB.submit()
        while res.status == 302:
            res = res.follow()
        assert_equal(res.status, 200)

        # finish registration of user B
        res = fvA.submit('save')
        assert_equal(res.status, 200)
        assert 'user_a__</a> is currently logged in' in res.body, res.body
        assert 'User "user_b_" is now registered but you are still logged in as "user_a__" from before'.replace('"', '&#34;') in res.body, res.body
        assert 'logout' in res.body, res.body

        # logout and login as user B
        res = self.app.get('/user/_logout')
        res2 = res.follow()
        while res2.status == 302:
            res2 = res2.follow()
        assert 'You have logged out successfully.' in res2, res2
        offset = url_for(controller='user', action='login')
        res = self.app.get(offset)
        fv = res.forms['login']
        fv['login'] = 'user_b_'
        fv['password'] = str(password)
        res = fv.submit()
        while res.status == 302:
            res = res.follow()
        assert_equal(res.status, 200)
        assert 'User B is now logged in' in res.body, res.body

    @search_related
    def test_home_login(self):
        offset = url_for('home')
        res = self.app.get(offset)
        res = res.click('Login')
        assert 'Login to CKAN' in res, res.body

    def test_apikey(self):
        username= u'okfntest'
        user = model.User.by_name(u'okfntest')
        if not user:
            user = model.User(name=u'okfntest')
            model.Session.add(user)
            model.Session.commit()
            model.Session.remove()

        # not logged in
        offset = url_for(controller='user', action='read', id=username)
        res = self.app.get(offset)
        assert not 'API key' in res

        offset = url_for(controller='user', action='read', id='okfntest')
        res = self.app.get(offset, extra_environ={'REMOTE_USER': 'okfntest'})
        assert user.apikey in res, res

    def test_user_create(self):
        # create/register user
        username = 'testcreate'
        fullname = u'Test Create'
        password = u'testpassword'
        email = u'test@test.org'
        assert not model.User.by_name(unicode(username))
        rev_id_before_test = model.repo.youngest_revision().id

        offset = url_for(controller='user', action='register')
        res = self.app.get(offset, status=200)
        main_res = self.main_div(res)
        assert 'Register' in main_res, main_res
        fv = res.forms['user-edit']
        fv['name'] = username
        fv['fullname'] = fullname
        fv['email'] = email
        fv['password1'] = password
        fv['password2'] = password
        res = fv.submit('save')

        # view user
        assert res.status == 302, self.main_div(res).encode('utf8')
        res = res.follow()
        if res.status == 302:
            res = res.follow()
        if res.status == 302:
            res = res.follow()
        if res.status == 302:
            res = res.follow()
        assert res.status == 200, res
        main_res = self.main_div(res)
        assert fullname in main_res, main_res

        # check saved user object
        user = model.User.by_name(unicode(username))
        assert user
        assert_equal(user.name, username)
        assert_equal(user.fullname, fullname)
        assert_equal(user.email, email)
        assert user.password

        # no revision should be created - User is not revisioned
        rev_id_after_test = model.repo.youngest_revision().id
        assert_equal(rev_id_before_test, rev_id_after_test)

        # check cookies created
        cookie = res.request.environ['HTTP_COOKIE']
        assert 'auth_tkt=' in cookie, cookie
        assert 'testcreate!userid_type:unicode' in cookie, cookie


    def test_user_create_unicode(self):
        # create/register user
        username = u'testcreate4'
        fullname = u'Test Create\xc2\xa0'
        password = u'testpassword\xc2\xa0'
        email = u'me\xc2\xa0@test.org'
        assert not model.User.by_name(username)

        offset = url_for(controller='user', action='register')
        res = self.app.get(offset, status=200)
        main_res = self.main_div(res)
        assert 'Register' in main_res, main_res
        fv = res.forms['user-edit']
        fv['name'] = username
        fv['fullname'] = fullname.encode('utf8')
        fv['email'] = email.encode('utf8')
        fv['password1'] = password.encode('utf8')
        fv['password2'] = password.encode('utf8')
        res = fv.submit('save')

        # view user
        assert res.status == 302, self.main_div(res).encode('utf8')
        res = res.follow()
        if res.status == 302:
            res = res.follow()
        if res.status == 302:
            res = res.follow()
        if res.status == 302:
            res = res.follow()
        assert res.status == 200, res
        main_res = self.main_div(res)
        assert fullname in main_res, main_res

        user = model.User.by_name(unicode(username))
        assert user
        assert_equal(user.name, username)
        assert_equal(user.fullname, fullname)
        assert_equal(user.email, email)
        assert user.password

    def test_user_create_no_name(self):
        # create/register user
        password = u'testpassword'

        offset = url_for(controller='user', action='register')
        res = self.app.get(offset, status=200)
        main_res = self.main_div(res)
        assert 'Register' in main_res, main_res
        fv = res.forms['user-edit']
        fv['password1'] = password
        fv['password2'] = password
        res = fv.submit('save')
        assert res.status == 200, res
        main_res = self.main_div(res)
        assert 'Name: Missing value' in main_res, main_res

    def test_user_create_bad_name(self):
        # create/register user
        username = u'%%%%%%' # characters not allowed
        password = 'testpass'

        offset = url_for(controller='user', action='register')
        res = self.app.get(offset, status=200)
        main_res = self.main_div(res)
        assert 'Register' in main_res, main_res
        fv = res.forms['user-edit']
        fv['name'] = username
        fv['password1'] = password
        fv['password2'] = password
        res = fv.submit('save')
        assert res.status == 200, res
        main_res = self.main_div(res)
        assert 'The form contains invalid entries' in main_res, main_res
        assert 'Url must be purely lowercase alphanumeric' in main_res
        self.check_named_element(main_res, 'input', 'name="name"', 'value="%s"' % username)

    def test_user_create_existing_name(self):
        # create/register user
        username = u'annafan'
        password = 'testpass'

        offset = url_for(controller='user', action='register')
        res = self.app.get(offset, status=200)
        main_res = self.main_div(res)
        assert 'Register' in main_res, main_res
        fv = res.forms['user-edit']
        fv['name'] = username
        fv['password1'] = password
        fv['password2'] = password
        res = fv.submit('save')
        assert res.status == 200, res
        main_res = self.main_div(res)
        assert 'The form contains invalid entries' in main_res, main_res
        assert 'That login name is not available' in main_res
        self.check_named_element(main_res, 'input', 'name="name"', 'value="%s"' % username)

    def test_user_create_bad_password(self):
        # create/register user
        username = 'testcreate2'
        password = u'a' # too short

        offset = url_for(controller='user', action='register')
        res = self.app.get(offset, status=200)
        main_res = self.main_div(res)
        assert 'Register' in main_res, main_res
        fv = res.forms['user-edit']
        fv['name'] = username
        fv['password1'] = password
        fv['password2'] = password
        res = fv.submit('save')
        assert res.status == 200, res
        main_res = self.main_div(res)
        assert 'password must be 4 characters or longer' in main_res, main_res
        self.check_named_element(main_res, 'input', 'name="name"', 'value="%s"' % username)

    def test_user_create_without_password(self):
        # create/register user
        username = 'testcreate3'
        user = model.User.by_name(unicode(username))

        offset = url_for(controller='user', action='register')
        res = self.app.get(offset, status=200)
        main_res = self.main_div(res)
        assert 'Register' in main_res, main_res
        fv = res.forms['user-edit']
        fv['name'] = username
        # no password
        res = fv.submit('save')
        assert res.status == 200, res
        main_res = self.main_div(res)
        assert 'Password: Please enter both passwords' in main_res, main_res
        self.check_named_element(main_res, 'input', 'name="name"', 'value="%s"' % username)

    def test_user_create_only_one_password(self):
        # create/register user
        username = 'testcreate4'
        password = u'testpassword'
        user = model.User.by_name(unicode(username))

        offset = url_for(controller='user', action='register')
        res = self.app.get(offset, status=200)
        main_res = self.main_div(res)
        assert 'Register' in main_res, main_res
        fv = res.forms['user-edit']
        fv['name'] = username
        fv['password1'] = password
        # Only password1
        res = fv.submit('save')
        assert res.status == 200, res
        main_res = self.main_div(res)
        assert 'Password: Please enter both passwords' in main_res, main_res
        self.check_named_element(main_res, 'input', 'name="name"', 'value="%s"' % username)

    def test_user_create_invalid_password(self):
        # create/register user
        username = 'testcreate4'
        password = u'tes' # Too short
        user = model.User.by_name(unicode(username))

        offset = url_for(controller='user', action='register')
        res = self.app.get(offset, status=200)
        main_res = self.main_div(res)
        assert 'Register' in main_res, main_res
        fv = res.forms['user-edit']
        fv['name'] = username
        fv['password1'] = password
        fv['password2'] = password
        res = fv.submit('save')
        assert res.status == 200, res
        main_res = self.main_div(res)
        assert 'Password: Your password must be 4 characters or longer' in main_res, main_res
        self.check_named_element(main_res, 'input', 'name="name"', 'value="%s"' % username)

    def test_user_create_missing_parameters(self):
        # create/register user
        username = 'testcreate4'
        user = model.User.by_name(unicode(username))
        password = u'testpassword'

        offset = url_for(controller='user', action='register')
        res = self.app.get(offset, status=200)
        main_res = self.main_div(res)
        assert 'Register' in main_res, main_res
        fv = res.forms['user-edit']
        fv['name'] = username
        fv['password1'] = password
        fv['password2'] = password
        del fv.fields['email']
        res = fv.submit('save')
        assert "Errors in form" in res.body
        assert "Email: Missing value" in res.body

    def test_user_edit(self):
        # create user
        username = 'testedit'
        about = u'Test About'
        user = model.User.by_name(unicode(username))
        if not user:
            model.Session.add(model.User(name=unicode(username), about=about,
                email=u'me@test.org',
                password='letmein'))
            model.repo.commit_and_remove()
            user = model.User.by_name(unicode(username))
        rev_id_before_test = model.repo.youngest_revision().id

        # edit
        new_about = u'Changed about'
        new_password = u'testpass'
        new_openid = u'http://mynewopenid.com/'
        offset = url_for(controller='user', action='edit', id=user.id)
        res = self.app.get(offset, status=200, extra_environ={'REMOTE_USER':username})
        main_res = self.main_div(res)
        assert 'Edit User: ' in main_res, main_res
        assert about in main_res, main_res
        fv = res.forms['user-edit']
        fv['about'] = new_about
        fv['openid'] = new_openid
        fv['password1'] = new_password
        fv['password2'] = new_password

        # commit
        res = fv.submit('save', extra_environ={'REMOTE_USER':username})
        assert res.status == 302, self.main_div(res).encode('utf8')
        res = res.follow()
        main_res = self.main_div(res)
        assert 'testedit' in main_res, main_res
        assert new_about in main_res, main_res

        updated_user = model.User.by_name(unicode(username))
        assert_equal(updated_user.openid, new_openid)

        # read, not logged in
        offset = url_for(controller='user', action='read', id=user.id)
        res = self.app.get(offset, status=200)
        main_res = self.main_div(res)
        assert new_about in main_res, main_res

        # no revision should be created - User is not revisioned
        rev_id_after_test = model.repo.youngest_revision().id
        assert_equal(rev_id_before_test, rev_id_after_test)

    def test_user_edit_no_password(self):
        # create user
        username = 'testedit2'
        about = u'Test About'
        user = model.User.by_name(unicode(username))
        if not user:
            model.Session.add(model.User(name=unicode(username), about=about,
                email=u'me@test.org',
                password='letmein'))
            model.repo.commit_and_remove()
            user = model.User.by_name(unicode(username))

        old_password = user.password

        # edit
        new_about = u'Changed about'
        offset = url_for(controller='user', action='edit', id=user.id)
        res = self.app.get(offset, status=200, extra_environ={'REMOTE_USER':username})
        main_res = self.main_div(res)
        assert 'Edit User: ' in main_res, main_res
        assert about in main_res, main_res
        fv = res.forms['user-edit']
        fv['about'] = new_about
        fv['password1'] = ''
        fv['password2'] = ''

        # commit
        res = fv.submit('save', extra_environ={'REMOTE_USER':username})
        assert res.status == 302, self.main_div(res).encode('utf8')
        res = res.follow()
        main_res = self.main_div(res)
        assert 'testedit2' in main_res, main_res
        assert new_about in main_res, main_res

        # read, not logged in
        offset = url_for(controller='user', action='read', id=user.id)
        res = self.app.get(offset, status=200)
        main_res = self.main_div(res)
        assert new_about in main_res, main_res

        updated_user = model.User.by_name(unicode(username))
        new_password = updated_user.password

        # Ensure password has not changed
        assert old_password == new_password

    def test_user_edit_no_name(self):
        # create user
        username = 'testedit3'
        about = u'Test About'
        user = model.User.by_name(unicode(username))
        if not user:
            model.Session.add(model.User(name=unicode(username), about=about,
                email=u'me@test.org',
                password='letmein'))
            model.repo.commit_and_remove()
            user = model.User.by_name(unicode(username))

        old_password = user.password

        # edit
        offset = url_for(controller='user', action='edit', id=user.id)
        res = self.app.get(offset, status=200, extra_environ={'REMOTE_USER':username})
        main_res = self.main_div(res)
        assert 'Edit User: ' in main_res, main_res
        fv = res.forms['user-edit']
        fv['name'] = ''

        # commit
        res = fv.submit('save', extra_environ={'REMOTE_USER':username})
        assert res.status == 200
        main_res = self.main_div(res)
        assert 'Name: Missing value' in main_res, main_res

    def test_user_edit_existing_user_name(self):
        # create user
        username = 'testedit3'
        about = u'Test About'
        user = model.User.by_name(unicode(username))
        if not user:
            model.Session.add(model.User(name=unicode(username), about=about,
                email=u'me@test.org',
                password='letmein'))
            model.repo.commit_and_remove()
            user = model.User.by_name(unicode(username))

        # edit
        offset = url_for(controller='user', action='edit', id=user.id)
        res = self.app.get(offset, status=200, extra_environ={'REMOTE_USER':username})
        main_res = self.main_div(res)
        assert 'Edit User: ' in main_res, main_res
        fv = res.forms['user-edit']
        fv['name'] = 'annafan'

        # commit
        res = fv.submit('save', extra_environ={'REMOTE_USER':username})
        assert res.status == 200
        main_res = self.main_div(res)
        assert 'Name: That login name is not available' in main_res, main_res

    def test_user_edit_no_user(self):
        offset = url_for(controller='user', action='edit', id=None)
        res = self.app.get(offset, status=400)
        assert 'No user specified' in res, res

    def test_user_edit_unknown_user(self):
        offset = url_for(controller='user', action='edit', id='unknown_person')
        res = self.app.get(offset, status=302) # redirect to login page
        res = res.follow()
        assert 'Login' in res, res

    def test_user_edit_not_logged_in(self):
        # create user
        username = 'testedit'
        about = u'Test About'
        user = model.User.by_name(unicode(username))
        if not user:
            model.Session.add(model.User(name=unicode(username), about=about,
                                         password='letmein'))
            model.repo.commit_and_remove()
            user = model.User.by_name(unicode(username))

        offset = url_for(controller='user', action='edit', id=username)
        res = self.app.get(offset, status=302)

    def test_edit_spammer(self):
        # create user
        username = 'testeditspam'
        about = u'Test About <a href="http://spamsite.net">spamsite</a>'
        user = model.User.by_name(unicode(username))
        if not user:
            model.Session.add(model.User(name=unicode(username), about=about,
                                         password='letmein'))
            model.repo.commit_and_remove()
            user = model.User.by_name(unicode(username))

        # edit
        offset = url_for(controller='user', action='edit', id=user.id)
        res = self.app.get(offset, status=200, extra_environ={'REMOTE_USER':username})
        main_res = self.main_div(res)
        assert 'Edit User: ' in main_res, main_res
        assert 'Test About &lt;a href="http://spamsite.net"&gt;spamsite&lt;/a&gt;' in main_res, main_res
        fv = res.forms['user-edit']
        # commit
        res = fv.submit('save', extra_environ={'REMOTE_USER':username})
        assert res.status == 200, res.status
        main_res = self.main_div(res)
        assert 'looks like spam' in main_res, main_res
        assert 'Edit User: ' in main_res, main_res

    def test_login_openid_error(self):
        # comes back as a params like this:
        # e.g. /user/login?error=Error%20in%20discovery:%20Error%20fetching%20XRDS%20document:%20(6,%20%22Couldn't%20resolve%20host%20'mysite.myopenid.com'%22)
        res = self.app.get("/user/login?error=Error%20in%20discovery:%20Error%20fetching%20XRDS%20document:%20(6,%20%22Couldn't%20resolve%20host%20'mysite.myopenid.com'%22")
        assert "Couldn&#39;t resolve host" in res, res

    def _login_openid(self, res):
        # this requires a valid account on some openid provider
        # (or for us to stub an open_id provider ...)
        assert 'Please Sign In' in res
        username = u'http://okfntest.myopenid.com'
        fv = res.forms['user-login']
        fv['passurl'] =  username
        web.submit()
        web.code(200)
        assert 'You must sign in to authenticate to' in res
        assert username in res
        fv['password'] =  u'okfntest'
        res = fv.submit()
        assert 'Please carefully verify whether you wish to trust' in res
        fv = res.forms[0]
        res = fv.submit('allow_once')
        # at this point we should return
        # but for some reason this does not work ...
        return res

    def test_request_reset_user_password_link_user_incorrect(self):
        offset = url_for(controller='user',
                         action='request_reset')
        res = self.app.get(offset)
        fv = res.forms['user-password-reset']
        fv['user'] = 'unknown'
        res = fv.submit()
        assert 'No such user: unknown' in res, res # error

    def test_request_reset_user_password_using_search(self):
        offset = url_for(controller='user',
                         action='request_reset')
        CreateTestData.create_user(name='larry1', fullname='kittens')
        CreateTestData.create_user(name='larry2', fullname='kittens')
        res = self.app.get(offset)
        fv = res.forms['user-password-reset']
        fv['user'] = 'kittens'
        res = fv.submit()
        assert '&#34;kittens&#34; matched several users' in res, res
        assert 'larry1' not in res, res
        assert 'larry2' not in res, res

        res = self.app.get(offset)
        fv = res.forms['user-password-reset']
        fv['user'] = ''
        res = fv.submit()
        assert 'No such user:' in res, res

        res = self.app.get(offset)
        fv = res.forms['user-password-reset']
        fv['user'] = 'l'
        res = fv.submit()
        assert 'No such user:' in res, res

    def test_reset_user_password_link(self):
        # Set password
        CreateTestData.create_user(name='bob', email='bob@bob.net', password='test1')

        # Set password to something new
        model.User.by_name(u'bob').password = 'test2'
        model.repo.commit_and_remove()
        test2_encoded = model.User.by_name(u'bob').password
        assert test2_encoded != 'test2'
        assert model.User.by_name(u'bob').password == test2_encoded

        # Click link from reset password email
        create_reset_key(model.User.by_name(u'bob'))
        reset_password_link = get_reset_link(model.User.by_name(u'bob'))
        offset = reset_password_link.replace('http://test.ckan.net', '')
        res = self.app.get(offset)

        # Reset password form
        fv = res.forms['user-reset']
        fv['password1'] = 'test1'
        fv['password2'] = 'test1'
        res = fv.submit('save', status=302)

        # Check a new password is stored
        assert model.User.by_name(u'bob').password != test2_encoded

    def test_perform_reset_user_password_link_key_incorrect(self):
        CreateTestData.create_user(name='jack', password='test1')
        # Make up a key - i.e. trying to hack this
        user = model.User.by_name(u'jack')
        offset = url_for(controller='user',
                         action='perform_reset',
                         id=user.id,
                         key='randomness') # i.e. incorrect
        res = self.app.get(offset, status=403) # error

    def test_perform_reset_user_password_link_key_missing(self):
        CreateTestData.create_user(name='jack', password='test1')
        user = model.User.by_name(u'jack')
        offset = url_for(controller='user',
                         action='perform_reset',
                         id=user.id)  # not, no key specified
        res = self.app.get(offset, status=403) # error


    def test_perform_reset_user_password_link_user_incorrect(self):
        # Make up a key - i.e. trying to hack this
        user = model.User.by_name(u'jack')
        offset = url_for(controller='user',
                         action='perform_reset',
                         id='randomness',  # i.e. incorrect
                         key='randomness')
        res = self.app.get(offset, status=404)
