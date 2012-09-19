from pylons.test import pylonsapp
import webtest

import ckan.tests as tests
import ckan.model as model


class WebAppTest(tests.BaseCase):
    '''
    Useful methods for debugging:
    =============================

    # dict of fields
    form.fields.values()

    # open the browser with the current page
    res.showbrowser()
    '''
    wsgiapp = pylonsapp
    assert wsgiapp, 'You need to run nose with --with-pylons'
    # Either that, or this file got imported somehow before the tests started
    # running, meaning the pylonsapp wasn't setup yet (which is done in
    # pylons.test.py:begin())
    app = webtest.TestApp(wsgiapp)

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()

    def log_in(self, res=None):
        self.app.reset()
        if not res:
            res = self.app.get(tests.url_for('home'))

        tests.CreateTestData.create_test_user()
        res = res.goto(tests.url_for(controller='user', action='login'))
        form = res.forms['login']

        form['login'] = 'tester'
        form['password'] = 'tester'

        res = self.auto_follow(form.submit())
        assert "tester is now logged in" in res

        return res

    def auto_follow(self, res):
        ''' Follows a series of redirects
        (no auto_follow=True support in res.get yet)
        '''
        if res.status == '302 Found':
            return self.auto_follow(res.follow())
        return res
