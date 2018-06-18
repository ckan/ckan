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

import collections
import contextlib
import errno
import functools
import logging
import os
import re

import webtest
import nose.tools
from nose.tools import assert_in, assert_not_in
import mock
import rq

from ckan.common import config
import ckan.lib.jobs as jobs
from ckan.lib.redis import connect_to_redis
import ckan.lib.search as search
import ckan.config.middleware
import ckan.model as model
import ckan.logic as logic


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
            self._flask_app = self.app.apps['flask_app']._wsgi_app
        return self._flask_app


def _get_test_app():
    '''Return a webtest.TestApp for CKAN, with legacy templates disabled.

    For functional tests that need to request CKAN pages or post to the API.
    Unit tests shouldn't need this.

    '''
    config['ckan.legacy_templates'] = False
    config['testing'] = True
    app = ckan.config.middleware.make_app(config['global_conf'], **config)
    app = CKANTestApp(app)
    return app


class FunctionalTestBase(object):
    '''A base class for functional test classes to inherit from.

    Allows configuration changes by overriding _apply_config_changes and
    resetting the CKAN config after your test class has run. It creates a
    webtest.TestApp at self.app for your class to use to make HTTP requests
    to the CKAN web UI or API. Also loads plugins defined by
    _load_plugins in the class definition.

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
        import ckan.plugins as p
        # Make a copy of the Pylons config, so we can restore it in teardown.
        cls._original_config = dict(config)
        cls._apply_config_changes(config)
        cls._get_test_app()
        for plugin in getattr(cls, '_load_plugins', []):
            p.load(plugin)

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
        import ckan.plugins as p
        for plugin in reversed(getattr(cls, '_load_plugins', [])):
            p.unload(plugin)
        # Restore the Pylons config to its original values, in case any tests
        # changed any config settings.
        config.clear()
        config.update(cls._original_config)


class RQTestBase(object):
    '''
    Base class for tests of RQ functionality.
    '''
    def setup(self):
        u'''
        Delete all RQ queues and jobs.
        '''
        # See https://github.com/nvie/rq/issues/731
        redis_conn = connect_to_redis()
        for queue in rq.Queue.all(connection=redis_conn):
            queue.empty()
            redis_conn.srem(rq.Queue.redis_queues_keys, queue._key)
            redis_conn.delete(queue._key)

    def all_jobs(self):
        u'''
        Get a list of all RQ jobs.
        '''
        jobs = []
        redis_conn = connect_to_redis()
        for queue in rq.Queue.all(connection=redis_conn):
            jobs.extend(queue.jobs)
        return jobs

    def enqueue(self, job=None, *args, **kwargs):
        u'''
        Enqueue a test job.
        '''
        if job is None:
            job = jobs.test_job
        return jobs.enqueue(job, *args, **kwargs)


class FunctionalRQTestBase(FunctionalTestBase, RQTestBase):
    '''
    Base class for functional tests of RQ functionality.
    '''
    def setup(self):
        FunctionalTestBase.setup(self)
        RQTestBase.setup(self)


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


# FIXME: remove webtest_* functions below when we upgrade webtest

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
    '''Decorator to temporarily change CKAN's config to a new value

    This allows you to easily create tests that need specific config values to
    be set, making sure it'll be reverted to what it was originally, after your
    test is run.

    Usage::

        @helpers.change_config('ckan.site_title', 'My Test CKAN')
        def test_ckan_site_title(self):
            assert config['ckan.site_title'] == 'My Test CKAN'

    :param key: the config key to be changed, e.g. ``'ckan.site_title'``
    :type key: string

    :param value: the new config key's value, e.g. ``'My Test CKAN'``
    :type value: string

    .. seealso:: The context manager :py:func:`changed_config`
    '''
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with changed_config(key, value):
                return func(*args, **kwargs)
        return wrapper
    return decorator


@contextlib.contextmanager
def changed_config(key, value):
    '''
    Context manager for temporarily changing a config value.

    Allows you to temporarily change the value of a CKAN configuration
    option. The original value is restored once the context manager is
    left.

    Usage::

        with changed_config(u'ckan.site_title', u'My Test CKAN'):
            assert config[u'ckan.site_title'] == u'My Test CKAN'

    .. seealso:: The decorator :py:func:`change_config`
    '''
    _original_config = config.copy()
    config[key] = value
    try:
        yield
    finally:
        config.clear()
        config.update(_original_config)


def mock_auth(auth_function_path):
    '''
    Decorator to easily mock a CKAN auth method in the context of a test
     function

    It adds a mock object for the provided auth_function_path as a parameter to
     the test function.

    Essentially it makes sure that `ckan.authz.clear_auth_functions_cache` is
     called before and after to make sure that the auth functions pick up
     the newly changed values.

    Usage::

        @helpers.mock_auth('ckan.logic.auth.create.package_create')
        def test_mock_package_create(self, mock_package_create):
            from ckan import logic
            mock_package_create.return_value = {'success': True}

            # package_create is mocked
            eq_(logic.check_access('package_create', {}), True)

            assert mock_package_create.called

    :param action_name: the full path to the auth function to be mocked,
        e.g. ``ckan.logic.auth.create.package_create``
    :type action_name: string

    '''
    from ckan.authz import clear_auth_functions_cache

    def decorator(func):
        def wrapper(*args, **kwargs):

            try:
                with mock.patch(auth_function_path) as mocked_auth:
                    clear_auth_functions_cache()
                    new_args = args + tuple([mocked_auth])
                    return_value = func(*new_args, **kwargs)
            finally:
                clear_auth_functions_cache()
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


@contextlib.contextmanager
def recorded_logs(logger=None, level=logging.DEBUG,
                  override_disabled=True, override_global_level=True):
    u'''
    Context manager for recording log messages.

    :param logger: The logger to record messages from. Can either be a
        :py:class:`logging.Logger` instance or a string with the
        logger's name. Defaults to the root logger.

    :param int level: Temporary log level for the target logger while
        the context manager is active. Pass ``None`` if you don't want
        the level to be changed. The level is automatically reset to its
        original value when the context manager is left.

    :param bool override_disabled: A logger can be disabled by setting
        its ``disabled`` attribute. By default, this context manager
        sets that attribute to ``False`` at the beginning of its
        execution and resets it when the context manager is left. Set
        ``override_disabled`` to ``False`` to keep the current value
        of the attribute.

    :param bool override_global_level: The ``logging.disable`` function
        allows one to install a global minimum log level that takes
        precedence over a logger's own level. By default, this context
        manager makes sure that the global limit is at most ``level``,
        and reduces it if necessary during its execution. Set
        ``override_global_level`` to ``False`` to keep the global limit.

    :returns: A recording log handler that listens to ``logger`` during
        the execution of the context manager.
    :rtype: :py:class:`RecordingLogHandler`

    Example::

        import logging

        logger = logging.getLogger(__name__)

        with recorded_logs(logger) as logs:
            logger.info(u'Hello, world!')

        logs.assert_log(u'info', u'world')
    '''
    if logger is None:
        logger = logging.getLogger()
    elif not isinstance(logger, logging.Logger):
        logger = logging.getLogger(logger)
    handler = RecordingLogHandler()
    old_level = logger.level
    manager_level = logger.manager.disable
    disabled = logger.disabled
    logger.addHandler(handler)
    try:
        if level is not None:
            logger.setLevel(level)
        if override_disabled:
            logger.disabled = False
        if override_global_level:
            if (level is None) and (manager_level > old_level):
                logger.manager.disable = old_level
            elif (level is not None) and (manager_level > level):
                logger.manager.disable = level
        yield handler
    finally:
        logger.handlers.remove(handler)
        logger.setLevel(old_level)
        logger.disabled = disabled
        logger.manager.disable = manager_level


class RecordingLogHandler(logging.Handler):
    u'''
    Log handler that records log messages for later inspection.

    You can inspect the recorded messages via the ``messages`` attribute
    (a dict that maps log levels to lists of messages) or by using
    ``assert_log``.

    This class is rarely useful on its own, instead use
    :py:func:`recorded_logs` to temporarily record log messages.
    '''
    def __init__(self, *args, **kwargs):
        super(RecordingLogHandler, self).__init__(*args, **kwargs)
        self.clear()

    def emit(self, record):
        self.messages[record.levelname.lower()].append(record.getMessage())

    def assert_log(self, level, pattern, msg=None):
        u'''
        Assert that a certain message has been logged.

        :param string pattern: A regex which the message has to match.
            The match is done using ``re.search``.

        :param string level: The message level (``'debug'``, ...).

        :param string msg: Optional failure message in case the expected
            log message was not logged.

        :raises AssertionError: If the expected message was not logged.
        '''
        compiled_pattern = re.compile(pattern)
        for log_msg in self.messages[level]:
            if compiled_pattern.search(log_msg):
                return
        if not msg:
            if self.messages[level]:
                lines = u'\n    '.join(self.messages[level])
                msg = (u'Pattern "{}" was not found in the log messages for '
                       + u'level "{}":\n    {}').format(pattern, level, lines)
            else:
                msg = (u'Pattern "{}" was not found in the log messages for '
                       + u'level "{}" (no messages were recorded for that '
                       + u'level).').format(pattern, level)
        raise AssertionError(msg)

    def clear(self):
        u'''
        Clear all captured log messages.
        '''
        self.messages = collections.defaultdict(list)
