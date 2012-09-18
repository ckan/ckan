from base import WebAppTest
from oktest import ok
from ckan.tests import url_for


class TestAccountCreation(WebAppTest):
    fixtures = ['users.json']

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
        res = self.auto_follow(res)

        ok(res).contains("Bar is now logged in")
        ok(res.pyquery('h1.page_heading span.username').text()) == 'foo_bar'
        ok(res.pyquery('h1.page_heading span.fullname').text()).contains('Foo Bar')
