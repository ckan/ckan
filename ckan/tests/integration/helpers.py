import ckan.tests as tests

'''Useful methods for debugging:
=============================

# dict of fields
form.fields.values()

# open the browser with the current page
res.showbrowser()
'''


def log_in(app, res=None):
    app.reset()
    if not res:
        res = app.get(tests.url_for('home'))

    tests.CreateTestData.create_test_user()
    res = res.goto(tests.url_for(controller='user', action='login'))
    form = res.forms['login']

    form['login'] = 'tester'
    form['password'] = 'tester'

    res = auto_follow(form.submit())
    assert "tester is now logged in" in res

    return res


def auto_follow(res):
    ''' Follows a series of redirects
    (no auto_follow=True support in res.get yet)
    '''
    if res.status == '302 Found':
        return auto_follow(res.follow())
    return res
