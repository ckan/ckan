from ckan.tests import url_for
from pylons.test import pylonsapp
import helpers
import webtest
import unittest


class TestAccountCreation(unittest.TestCase):
    assert pylonsapp, 'You need to run nose with --with-pylons'
    app = webtest.TestApp(pylonsapp)

    def test_create_account(self):
        res = self.app.get(url_for('home'))
        res = res.click(description="Register", index=0)

        form = res.forms[u'user-edit']

        form['name'] = 'foo_bar'
        form['fullname'] = 'Foo Bar'
        form['email'] = 'foo@bar.com'
        form['password1'] = 'secret'
        form['password2'] = 'secret'

        res = form.submit(name='save')
        res = helpers.auto_follow(res)

        assert "Bar is now logged in" in res
        assert res.pyquery('h1.page_heading span.username').text() == 'foo_bar'
        assert 'Foo Bar' in res.pyquery('h1.page_heading span.fullname').text()
