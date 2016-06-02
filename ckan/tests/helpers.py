# encoding: utf-8

'''This is a collection of helper functions for use in tests.

We want to avoid sharing test helper functions between test modules as
much as possible, and we definitely don't want to share test fixtures between
test modules, or to introduce a complex hierarchy of test class subclasses,
etc.

We want to reduce the amount of "travel" that a reader needs to undertake to
understand a test method -- reducing the number of other files they need to go
and read to understand what the test code does. And we want to avoid tightly
coupling test modules to each other by having them share code.

But some test helper functions just increase the readability of tests so much
and make writing tests so much easier, that it's worth having them despite the
potential drawbacks.

This module is reserved for these very useful functions.

'''
import webtest
from pylons import config
import nose.tools
import mock

import ckan.lib.search as search
import ckan.config.middleware
import ckan.model as model
import ckan.logic as logic


try:
    from nose.tools import assert_in, assert_not_in
except ImportError:
    # Python 2.6 doesn't have these, so define them here
    def assert_in(a, b, msg=None):
        assert a in b, msg or '%r was not in %r' % (a, b)

    def assert_not_in(a, b, msg=None):
        assert a not in b, msg or '%r was in %r' % (a, b)


def reset_db():
    '''Reset CKAN's database.

    If a test class uses the database, then it should call this function in its
    ``setup()`` method to make sure that it has a clean database to start with
    (nothing left over from other test classes or from previous test runs).

    If a test class doesn't use the database (and most test classes shouldn't
    need to) then it doesn't need to call this function.

    :returns: ``None``

    '''
    # Close any database connections that have been left open.
    # This prevents CKAN from hanging waiting for some unclosed connection.
    model.Session.close_all()

    model.repo.rebuild_db()


def call_action(action_name, context=None, **kwargs):
    '''Call the named ``ckan.logic.action`` function and return the result.

    This is just a nicer way for user code to call action functions, nicer than
    either calling the action function directly or via
    :py:func:`ckan.logic.get_action`.

    For example::

        user_dict = call_action('user_create', name='seanh',
                                email='seanh@seanh.com', password='pass')

    Any keyword arguments given will be wrapped in a dict and passed to the
    action function as its ``data_dict`` argument.

    Note: this skips authorization! It passes 'ignore_auth': True to action
    functions in their ``context`` dicts, so the corresponding authorization
    functions will not be run.
    This is because ckan.tests.logic.action tests only the actions, the
    authorization functions are tested separately in
    ckan.tests.logic.auth.
    See the :doc:`testing guidelines </contributing/testing>` for more info.

    This function should eventually be moved to
    :py:func:`ckan.logic.call_action` and the current
    :py:func:`ckan.logic.get_action` function should be
    deprecated. The tests may still need their own wrapper function for
    :py:func:`ckan.logic.call_action`, e.g. to insert ``'ignore_auth': True``
    into the ``context`` dict.

    :param action_name: the name of the action function to call, e.g.
        ``'user_update'``
    :type action_name: string
    :param context: the context dict to pass to the action function
        (optional, if no context is given a default one will be supplied)
    :type context: dict
    :returns: the dict or other value that the action function returns

    '''
    if context is None:
        context = {}
    context.setdefault('user', '127.0.0.1')
    context.setdefault('ignore_auth', True)
    return logic.get_action(action_name)(context=context, data_dict=kwargs)


def call_auth(auth_name, context, **kwargs):
    '''Call the named ``ckan.logic.auth`` function and return the result.

    This is just a convenience function for tests in
    :py:mod:`ckan.tests.logic.auth` to use.

    Usage::

        result = helpers.call_auth('user_update', context=context,
                                   id='some_user_id',
                                   name='updated_user_name')

    :param auth_name: the name of the auth function to call, e.g.
        ``'user_update'``
    :type auth_name: string

    :param context: the context dict to pass to the auth function, must
        contain ``'user'`` and ``'model'`` keys,
        e.g. ``{'user': 'fred', 'model': my_mock_model_object}``
    :type context: dict

    :returns: the dict that the auth function returns, e.g.
        ``{'success': True}`` or ``{'success': False, msg: '...'}``
        or just ``{'success': False}``
    :rtype: dict

    '''
    assert 'user' in context, ('Test methods must put a user name in the '
                               'context dict')
    assert 'model' in context, ('Test methods must put a model in the '
                                'context dict')

    return logic.check_access(auth_name, context, data_dict=kwargs)


class CKANTestApp(webtest.TestApp):
    '''A wrapper around webtest.TestApp

    It adds some convenience methods for CKAN
    '''

    _flask_app = None

    @property
    def flask_app(self):
        if not self._flask_app:
            self._flask_app = find_flask_app(self)
        return self._flask_app


def _get_test_app():
    '''Return a webtest.TestApp for CKAN, with legacy templates disabled.

    For functional tests that need to request CKAN pages or post to the API.
    Unit tests shouldn't need this.

    '''
    config['ckan.legacy_templates'] = False
    app = ckan.config.middleware.make_app(config['global_conf'], **config)
    app = CKANTestApp(app)
    return app


class FunctionalTestBase(object):
    '''A base class for functional test classes to inherit from.

    Allows configuration changes by overriding _apply_config_changes and
    resetting the CKAN config after your test class has run. It creates a
    webtest.TestApp at self.app for your class to use to make HTTP requests
    to the CKAN web UI or API.

    If you're overriding methods that this class provides, like setup_class()
    and teardown_class(), make sure to use super() to call this class's methods
    at the top of yours!

    '''
    @classmethod
    def _get_test_app(cls):  # leading _ because nose is terrible
        # FIXME: remove this method and switch to using helpers.get_test_app
        # in each test once the old functional tests are fixed or removed
        if not hasattr(cls, '_test_app'):
            cls._test_app = _get_test_app()
        return cls._test_app

    @classmethod
    def setup_class(cls):
        # Make a copy of the Pylons config, so we can restore it in teardown.
        cls._original_config = dict(config)
        cls._apply_config_changes(config)
        cls._get_test_app()

    @classmethod
    def _apply_config_changes(cls, cfg):
        pass

    def setup(self):
        '''Reset the database and clear the search indexes.'''
        reset_db()
        if hasattr(self, '_test_app'):
            self._test_app.reset()
        search.clear_all()

    @classmethod
    def teardown_class(cls):
        # Restore the Pylons config to its original values, in case any tests
        # changed any config settings.
        config.clear()
        config.update(cls._original_config)


def submit_and_follow(app, form, extra_environ=None, name=None,
                      value=None, **args):
    '''
    Call webtest_submit with name/value passed expecting a redirect
    and return the response from following that redirect.
    '''
    response = webtest_submit(form, name, value=value, status=302,
                              extra_environ=extra_environ, **args)
    return app.get(url=response.headers['Location'],
                   extra_environ=extra_environ)


## FIXME: remove webtest_* functions below when we upgrade webtest

def webtest_submit(form, name=None, index=None, value=None, **args):
    '''
    backported version of webtest.Form.submit that actually works
    for submitting with different submit buttons.

    We're stuck on an old version of webtest because we're stuck
    on an old version of webob because we're stuck on an old version
    of Pylons. This prolongs our suffering, but on the bright side
    it lets us have functional tests that work.
    '''
    fields = webtest_submit_fields(form, name, index=index, submit_value=value)
    if form.method.upper() != "GET":
        args.setdefault("content_type",  form.enctype)
    return form.response.goto(form.action, method=form.method,
                              params=fields, **args)


def webtest_submit_fields(form, name=None, index=None, submit_value=None):
    '''
    backported version of webtest.Form.submit_fields that actually works
    for submitting with different submit buttons.
    '''
    from webtest.app import File
    submit = []
    # Use another name here so we can keep function param the same for BWC.
    submit_name = name
    if index is not None and submit_value is not None:
        raise ValueError("Can't specify both submit_value and index.")

    # If no particular button was selected, use the first one
    if index is None and submit_value is None:
        index = 0

    # This counts all fields with the submit name not just submit fields.
    current_index = 0
    for name, field in form.field_order:
        if name is None:  # pragma: no cover
            continue
        if submit_name is not None and name == submit_name:
            if index is not None and current_index == index:
                submit.append((name, field.value_if_submitted()))
            if submit_value is not None and \
               field.value_if_submitted() == submit_value:
                submit.append((name, field.value_if_submitted()))
            current_index += 1
        else:
            value = field.value
            if value is None:
                continue
            if isinstance(field, File):
                submit.append((name, field))
                continue
            if isinstance(value, list):
                for item in value:
                    submit.append((name, item))
            else:
                submit.append((name, value))
    return submit


def webtest_maybe_follow(response, **kw):
    """
    Follow all redirects. If this response is not a redirect, do nothing.
    Returns another response object.

    (backported from WebTest 2.0.1)
    """
    remaining_redirects = 100  # infinite loops protection

    while 300 <= response.status_int < 400 and remaining_redirects:
        response = response.follow(**kw)
        remaining_redirects -= 1

    assert remaining_redirects > 0, "redirects chain looks infinite"
    return response


def change_config(key, value):
    '''Decorator to temporarily changes Pylons' config to a new value

    This allows you to easily create tests that need specific config values to
    be set, making sure it'll be reverted to what it was originally, after your
    test is run.

    Usage::

        @helpers.change_config('ckan.site_title', 'My Test CKAN')
        def test_ckan_site_title(self):
            assert pylons.config['ckan.site_title'] == 'My Test CKAN'

    :param key: the config key to be changed, e.g. ``'ckan.site_title'``
    :type key: string

    :param value: the new config key's value, e.g. ``'My Test CKAN'``
    :type value: string
    '''
    def decorator(func):
        def wrapper(*args, **kwargs):
            _original_config = config.copy()
            config[key] = value

            try:
                return_value = func(*args, **kwargs)
            finally:
                config.clear()
                config.update(_original_config)

            return return_value
        return nose.tools.make_decorator(func)(wrapper)
    return decorator


def mock_action(action_name):
    '''
    Decorator to easily mock a CKAN action in the context of a test function

    It adds a mock object for the provided action as a parameter to the test
    function. The mock is discarded at the end of the function, even if there
    is an exception raised.

    Note that this mocks the action both when it's called directly via
    ``ckan.logic.get_action`` and via ``ckan.plugins.toolkit.get_action``.

    Usage::

        @mock_action('user_list')
        def test_mock_user_list(self, mock_user_list):

            mock_user_list.return_value = 'hi'

            # user_list is mocked
            eq_(helpers.call_action('user_list', {}), 'hi')

            assert mock_user_list.called

    :param action_name: the name of the action to be mocked,
        e.g. ``package_create``
    :type action_name: string

    '''
    def decorator(func):
        def wrapper(*args, **kwargs):
            mock_action = mock.MagicMock()

            from ckan.logic import get_action as original_get_action

            def side_effect(called_action_name):
                if called_action_name == action_name:
                    return mock_action
                else:
                    return original_get_action(called_action_name)
            try:
                with mock.patch('ckan.logic.get_action') as mock_get_action, \
                        mock.patch('ckan.plugins.toolkit.get_action') \
                        as mock_get_action_toolkit:
                    mock_get_action.side_effect = side_effect
                    mock_get_action_toolkit.side_effect = side_effect

                    new_args = args + tuple([mock_action])
                    return_value = func(*new_args, **kwargs)
            finally:
                # Make sure to stop the mock, even with an exception
                mock_action.stop()
            return return_value

        return nose.tools.make_decorator(func)(wrapper)
    return decorator


def set_extra_environ(key, value):
    '''Decorator to temporarily changes a single request environemnt value

    Create a new test app and use the a side effect of making a request
    to set an extra_environ value. Reset the value to '' after the test.

    Usage::

        @helpers.extra_environ('SCRIPT_NAME', '/myscript')
        def test_ckan_thing_affected_by_script_name(self):
            # ...

    :param key: the extra_environ key to be changed, e.g. ``'SCRIPT_NAME'``
    :type key: string

    :param value: the new extra_environ key's value, e.g. ``'/myscript'``
    :type value: string
    '''
    def decorator(func):
        def wrapper(*args, **kwargs):
            app = _get_test_app()
            app.get('/', extra_environ={key: value})

            try:
                return_value = func(*args, **kwargs)
            finally:
                app.get('/', extra_environ={key: ''})

            return return_value
        return nose.tools.make_decorator(func)(wrapper)
    return decorator


def find_flask_app(test_app):
    '''
    Helper function to recursively search the wsgi stack in `test_app` until
    the flask_app is discovered.

    Relies on each layer of the stack having a reference to the app they
    wrap in either a .app attribute or .apps list.
    '''
    if isinstance(test_app, ckan.config.middleware.CKANFlask):
        return test_app

    try:
        app = test_app.apps['flask_app'].app
    except (AttributeError, KeyError):
        pass
    else:
        return find_flask_app(app)

    try:
        app = test_app.app
    except AttributeError:
        print('No .app attribute. '
              'Have all layers of the stack got '
              'a reference to the app they wrap?')
    else:
        return find_flask_app(app)
