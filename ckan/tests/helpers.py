# encoding: utf-8

"""This is a collection of helper functions for use in tests.

We want to avoid sharing test helper functions between test modules as
much as possible, and we definitely don't want to introduce a complex
hierarchy of test class subclasses, etc.

We want to reduce the amount of "travel" that a reader needs to undertake to
understand a test method -- reducing the number of other files they need to go
and read to understand what the test code does. And we want to avoid tightly
coupling test modules to each other by having them share code.

But some test helper functions just increase the readability of tests so much
and make writing tests so much easier, that it's worth having them despite the
potential drawbacks.

New in CKAN 2.9: Consider using :ref:`fixtures` whenever possible for setting
up the initial state of a test or to create helpers objects like client apps.

"""

import collections
import contextlib
import functools
import logging
import re
import json
import smtplib

from flask.testing import Client as FlaskClient
from flask.wrappers import Response
from click.testing import CliRunner
import pytest
import mock
import rq
import six

from ckan.common import config
import ckan.lib.jobs as jobs
from ckan.lib.redis import connect_to_redis
import ckan.lib.search as search
import ckan.config.middleware
import ckan.model as model
import ckan.logic as logic

log = logging.getLogger(__name__)


def reset_db():
    """Reset CKAN's database.

    Rather than use this function directly, use the ``clean_db`` fixture
    either for all tests in a class::

        @pytest.mark.usefixtures("clean_db")
        class TestExample(object):

            def test_example(self):

    or for a single test::

        class TestExample(object):

            @pytest.mark.usefixtures("clean_db")
            def test_example(self):


    If a test class uses the database, then it may call this function in its
    ``setup()`` method to make sure that it has a clean database to start with
    (nothing left over from other test classes or from previous test runs).

    If a test class doesn't use the database (and most test classes shouldn't
    need to) then it doesn't need to call this function.

    :returns: ``None``

    """
    # Close any database connections that have been left open.
    # This prevents CKAN from hanging waiting for some unclosed connection.
    model.Session.close_all()

    model.repo.rebuild_db()


def call_action(action_name, context=None, **kwargs):
    """Call the named ``ckan.logic.action`` function and return the result.

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

    """
    if context is None:
        context = {}
    context.setdefault("user", "127.0.0.1")
    context.setdefault("ignore_auth", True)
    return logic.get_action(action_name)(context=context, data_dict=kwargs)


def call_auth(auth_name, context, **kwargs):
    """Call the named ``ckan.logic.auth`` function and return the result.

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

    """
    assert "user" in context, (
        "Test methods must put a user name in the " "context dict"
    )
    assert "model" in context, (
        "Test methods must put a model in the " "context dict"
    )

    return logic.check_access(auth_name, context, data_dict=kwargs)


def body_contains(res, content):
    try:
        body = res.data
    except AttributeError:
        body = res.body
    body = six.ensure_text(body)
    return content in body


class CKANCliRunner(CliRunner):
    def invoke(self, *args, **kwargs):
        # prevent cli runner from str/bytes exceptions
        kwargs.setdefault(u'complete_var', u'_CKAN_COMPLETE')
        return super(CKANCliRunner, self).invoke(*args, **kwargs)


class CKANResponse(Response):
    @property
    def body(self):
        return six.ensure_str(self.data)

    def __contains__(self, segment):
        return body_contains(self, segment)


class CKANTestApp(object):
    """A wrapper around flask.testing.Client

    It adds some convenience methods for CKAN
    """

    _flask_app = None

    @property
    def flask_app(self):
        if not self._flask_app:
            if six.PY2:
                self._flask_app = self.app.apps["flask_app"]._wsgi_app
            else:
                self._flask_app = self.app._wsgi_app
        return self._flask_app

    def __init__(self, app):
        self.app = app

    def test_client(self, use_cookies=True):
        return CKANTestClient(self.app, CKANResponse, use_cookies=use_cookies)
        self.flask_app.test_client_class = CKANTestClient
        return self.flask_app.test_client()

    def options(self, url, *args, **kwargs):
        res = self.test_client().options(url, *args, **kwargs)
        return res

    def post(self, url, *args, **kwargs):
        params = kwargs.pop("params", None)
        if params:
            kwargs["data"] = params
        res = self.test_client().post(url, *args, **kwargs)
        return res

    def get(self, url, *args, **kwargs):
        params = kwargs.pop("params", None)
        if params:
            kwargs["query_string"] = params

        res = self.test_client().get(url, *args, **kwargs)
        return res

    @property
    def json(self):
        return json.loads(self.data)


class CKANTestClient(FlaskClient):
    def open(self, *args, **kwargs):
        # extensions with support of CKAN<2.9 can use this parameter
        # to make errors of webtest.TestApp more verbose. FlaskClient
        # doesn't have anything similar, so we'll just drop this
        # parameter for backward compatibility and ask for updating
        # the code when possible.
        if kwargs.pop('expect_errors', None):
            log.warning(
                '`expect_errors` parameter passed to `test_app.post` '
                'has no effect. Remove it or pass conditionally, for '
                'CKAN version prior 2.9.0.'
            )

        status = kwargs.pop("status", None)
        extra_environ = kwargs.pop("extra_environ", None)
        if extra_environ:
            kwargs["environ_overrides"] = extra_environ

        if args and isinstance(args[0], six.string_types):
            kwargs.setdefault("follow_redirects", True)
            kwargs.setdefault("base_url", config["ckan.site_url"])
        res = super(CKANTestClient, self).open(*args, **kwargs)

        if status:
            assert (
                res.status_code == status
            ), "Actual: {}. Expected: {}".format(res.status_code, status)

        return res


def _get_test_app():
    """Return a CKANTestApp.

    Don't use this function directly, use the ``app`` fixture::

        def test_dataset_search(self, app):

            url = h.url_for('dataset.search')

            response = app.get(url)


    For functional tests that need to request CKAN pages or post to the API.
    Unit tests shouldn't need this.

    """
    config["ckan.legacy_templates"] = False
    config["testing"] = True
    if six.PY2:
        app = ckan.config.middleware.make_app(config)
    else:
        app = ckan.config.middleware.make_app(config)
    app = CKANTestApp(app)

    return app


class FunctionalTestBase(object):
    """A base class for functional test classes to inherit from.

    Deprecated: Use the ``app``, ``clean_db``, ``ckan_config`` and
    ``with_plugins`` ref:`fixtures` as needed to create functional test
    classes, eg::

        @pytest.mark.ckan_config('ckan.plugins', 'image_view')
        @pytest.mark.usefixtures('with_plugins')
        @pytest.mark.usefixtures('clean_db')
        class TestDatasetSearch(object):

            def test_dataset_search(self, app):

                url = h.url_for('dataset.search')
                response = app.get(url)

    Allows configuration changes by overriding _apply_config_changes and
    resetting the CKAN config after your test class has run. It creates a
    CKANTestApp at self.app for your class to use to make HTTP requests
    to the CKAN web UI or API. Also loads plugins defined by
    _load_plugins in the class definition.

    If you're overriding methods that this class provides, like setup_class()
    and teardown_class(), make sure to use super() to call this class's methods
    at the top of yours!

    """

    @classmethod
    def _get_test_app(cls):
        # FIXME: remove this method and switch to using helpers.get_test_app
        # in each test once the old functional tests are fixed or removed
        if not hasattr(cls, "_test_app"):
            cls._test_app = _get_test_app()
        return cls._test_app

    @classmethod
    def setup_class(cls):
        import ckan.plugins as p

        # Make a copy of the Pylons config, so we can restore it in teardown.
        cls._original_config = dict(config)
        cls._apply_config_changes(config)
        try:
            config["ckan.plugins"] = " ".join(cls._load_plugins)
            del cls._test_app  # reload with the new plugins
        except AttributeError:
            pass
        cls._get_test_app()

    @classmethod
    def _apply_config_changes(cls, cfg):
        pass

    def setup(self):
        """Reset the database and clear the search indexes."""
        reset_db()
        if hasattr(self, "_test_app"):
            self._test_app.reset()
        search.clear_all()

    @classmethod
    def teardown_class(cls):
        import ckan.plugins as p

        for plugin in reversed(getattr(cls, "_load_plugins", [])):
            p.unload(plugin)
        # Restore the Pylons config to its original values, in case any tests
        # changed any config settings.
        config.clear()
        config.update(cls._original_config)


@pytest.mark.usefixtures("with_test_worker")
class RQTestBase(object):
    """
    Base class for tests of RQ functionality.
    """

    def setup(self):
        u"""
        Delete all RQ queues and jobs.
        """
        # See https://github.com/nvie/rq/issues/731
        redis_conn = connect_to_redis()
        for queue in rq.Queue.all(connection=redis_conn):
            queue.empty()
            redis_conn.srem(rq.Queue.redis_queues_keys, queue._key)
            redis_conn.delete(queue._key)

    def all_jobs(self):
        u"""
        Get a list of all RQ jobs.
        """
        jobs = []
        redis_conn = connect_to_redis()
        for queue in rq.Queue.all(connection=redis_conn):
            jobs.extend(queue.jobs)
        return jobs

    def enqueue(self, job=None, *args, **kwargs):
        u"""
        Enqueue a test job.
        """
        if job is None:
            job = jobs.test_job
        return jobs.enqueue(job, *args, **kwargs)


@pytest.mark.usefixtures("clean_db", "with_plugins")
class FunctionalRQTestBase(RQTestBase):
    """
    Base class for functional tests of RQ functionality.
    """

    def setup(self):
        RQTestBase.setup(self)


def change_config(key, value):
    """Decorator to temporarily change CKAN's config to a new value

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
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with changed_config(key, value):
                return func(*args, **kwargs)

        return wrapper

    return decorator


@contextlib.contextmanager
def changed_config(key, value):
    """
    Context manager for temporarily changing a config value.

    Allows you to temporarily change the value of a CKAN configuration
    option. The original value is restored once the context manager is
    left.

    Usage::

        with changed_config(u'ckan.site_title', u'My Test CKAN'):
            assert config[u'ckan.site_title'] == u'My Test CKAN'

    .. seealso:: The decorator :py:func:`change_config`
    """
    _original_config = config.copy()
    config[key] = value
    try:
        yield
    finally:
        config.clear()
        config.update(_original_config)


@contextlib.contextmanager
def recorded_logs(
    logger=None,
    level=logging.DEBUG,
    override_disabled=True,
    override_global_level=True,
):
    u"""
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
    """
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
    u"""
    Log handler that records log messages for later inspection.

    You can inspect the recorded messages via the ``messages`` attribute
    (a dict that maps log levels to lists of messages) or by using
    ``assert_log``.

    This class is rarely useful on its own, instead use
    :py:func:`recorded_logs` to temporarily record log messages.
    """

    def __init__(self, *args, **kwargs):
        super(RecordingLogHandler, self).__init__(*args, **kwargs)
        self.clear()

    def emit(self, record):
        self.messages[record.levelname.lower()].append(record.getMessage())

    def assert_log(self, level, pattern, msg=None):
        u"""
        Assert that a certain message has been logged.

        :param string pattern: A regex which the message has to match.
            The match is done using ``re.search``.

        :param string level: The message level (``'debug'``, ...).

        :param string msg: Optional failure message in case the expected
            log message was not logged.

        :raises AssertionError: If the expected message was not logged.
        """
        compiled_pattern = re.compile(pattern)
        for log_msg in self.messages[level]:
            if compiled_pattern.search(log_msg):
                return
        if not msg:
            if self.messages[level]:
                lines = u"\n    ".join(self.messages[level])
                msg = (
                    u'Pattern "{}" was not found in the log messages for '
                    + u'level "{}":\n    {}'
                ).format(pattern, level, lines)
            else:
                msg = (
                    u'Pattern "{}" was not found in the log messages for '
                    + u'level "{}" (no messages were recorded for that '
                    + u"level)."
                ).format(pattern, level)
        raise AssertionError(msg)

    def clear(self):
        u"""
        Clear all captured log messages.
        """
        self.messages = collections.defaultdict(list)


class FakeSMTP(smtplib.SMTP):
    """Mock `SMTP` client, catching all the messages.
    """

    connect = mock.Mock()
    ehlo = mock.Mock()
    starttls = mock.Mock()
    login = mock.Mock()
    quit = mock.Mock()

    def __init__(self):
        self._msgs = []

    def __call__(self, *args):
        return self

    def get_smtp_messages(self):
        return self._msgs

    def clear_smtp_messages(self):
        self._msgs = []

    def sendmail(
        self, from_addr, to_addrs, msg, mail_options=(), rcpt_options=()
    ):
        """Just store message inside current instance.
        """
        self._msgs.append((None, from_addr, to_addrs, msg))
