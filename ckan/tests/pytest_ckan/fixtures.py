"""This is a collection of pytest fixtures for use in tests.

All fixtures below are available wherever CKAN is installed.
Any external CKAN extension should be able to include them directly into
their tests.

There are three type of fixtures available in CKAN:

* Fixtures that have some side-effect. They don't return any useful
  value and generally should be injected via
  ``pytest.mark.usefixtures``. Ex.: `with_plugins`, `clean_db`,
  `clean_index`.

* Fixtures that provide value. Ex. `app`

* Fixtures that provide factory function. They are rarely needed, so
  prefer using 'side-effect' or 'value' fixtures. Main use-case when
  one may use function-fixture - late initialization or repeatable
  execution(ex.: cleaning database more than once in a single
  test). But presence of these fixtures in test usually signals that
  is's a good time to refactor this test.

Deeper explanation can be found in `official documentation
<https://docs.pytest.org/en/latest/fixture.html>`_

"""
from __future__ import annotations

import copy
import smtplib
import itertools

from io import BytesIO
from typing import Any, IO, cast
from unittest import mock
from collections.abc import Iterable, Callable
import pytest
import rq

from werkzeug.datastructures import FileStorage as FlaskFileStorage
from pytest_factoryboy import register

import ckan.tests.helpers as test_helpers
import ckan.tests.factories as factories

import ckan.plugins
import ckan.cli
import ckan.model as model
from ckan import types
from ckan.common import config
from ckan.lib import redis, search


@register
class UserFactory(factories.User):
    pass


@register
class ResourceFactory(factories.Resource):
    pass


@register
class ResourceViewFactory(factories.ResourceView):
    pass


@register
class GroupFactory(factories.Group):
    pass


@register
class PackageFactory(factories.Dataset):
    pass


@register
class VocabularyFactory(factories.Vocabulary):
    pass


@register
class TagFactory(factories.Tag):
    pass


@register
class SystemInfoFactory(factories.SystemInfo):
    pass


@register
class APITokenFactory(factories.APIToken):
    pass


class SysadminFactory(factories.Sysadmin):
    pass


class SysadminWithTokenFactory(factories.SysadminWithToken):
    pass


class UserWithTokenFactory(factories.UserWithToken):
    pass


class OrganizationFactory(factories.Organization):
    pass


register(SysadminFactory, "sysadmin")
register(SysadminWithTokenFactory, "sysadmin_with_token")
register(UserWithTokenFactory, "user_with_token")
register(OrganizationFactory, "organization")


@pytest.fixture
def ckan_config(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch):
    """Allows to override the configuration object used by tests

    Takes into account config patches introduced by the ``ckan_config``
    mark.

    If you just want to set one or more configuration options for the
    scope of a test (or a test class), use the ``ckan_config`` mark::

        @pytest.mark.ckan_config('ckan.auth.create_unowned_dataset', True)
        def test_auth_create_unowned_dataset():

            # ...

    To use the custom config inside a test, apply the
    ``ckan_config`` mark to it and inject the ``ckan_config`` fixture:

    .. literalinclude:: /../ckan/tests/pytest_ckan/test_fixtures.py
       :start-after: # START-CONFIG-OVERRIDE
       :end-before: # END-CONFIG-OVERRIDE

    If the change only needs to be applied locally, use the
    ``monkeypatch`` fixture

    .. literalinclude:: /../ckan/tests/test_common.py
       :start-after: # START-CONFIG-OVERRIDE
       :end-before: # END-CONFIG-OVERRIDE

    """
    _original = copy.deepcopy(config)
    for mark in request.node.iter_markers(u"ckan_config"):
        monkeypatch.setitem(config, *mark.args)

    yield config
    config.clear()
    config.update(_original)


@pytest.fixture
def make_app(ckan_config: types.FixtureCkanConfig):
    """Factory for client app instances.

    Unless you need to create app instances lazily for some reason,
    use the ``app`` fixture instead.
    """
    from ckan.lib.app_globals import _CONFIG_CACHE
    # Reset values cached during the previous tests. Otherwise config values
    # that were added to app_globals reset the patched versions from
    # `ckan_config` mark.
    _CONFIG_CACHE.clear()

    return test_helpers._get_test_app


@pytest.fixture
def app(make_app: types.FixtureMakeApp):
    """Returns a client app instance to use in functional tests

    To use it, just add the ``app`` parameter to your test function signature::

        def test_dataset_search(self, app):

            url = h.url_for('dataset.search')

            response = app.get(url)


    """
    return make_app()


@pytest.fixture
def cli(ckan_config: types.FixtureCkanConfig):
    """Provides object for invoking CLI commands from tests.

    This is subclass of `click.testing.CliRunner`, so all examples
    from `Click docs
    <https://click.palletsprojects.com/en/master/testing/>`_ are valid
    for it.

    """
    env = {
        u'CKAN_INI': ckan_config[u'__file__']
    }
    return test_helpers.CKANCliRunner(env=env)


@pytest.fixture(scope=u"session")
def reset_db():
    """Callable for resetting the database to the initial state.

    If possible use the ``clean_db`` fixture instead.

    """
    factories.fake.unique.clear()
    return test_helpers.reset_db


@pytest.fixture(scope=u"session")
def reset_index():
    """Callable for cleaning search index.

    If possible use the ``clean_index`` fixture instead.
    """
    return search.clear_all


def _empty_queues():

    conn = redis.connect_to_redis()
    for queue in rq.Queue.all(connection=conn):
        queue.empty()
        queue.delete()


@pytest.fixture(scope=u"session")
def reset_queues():
    """Callable for emptying and deleting the queues.

    If possible use the ``clean_queues`` fixture instead.
    """
    return _empty_queues


@pytest.fixture(scope="session")
def reset_redis():
    """Callable for removing all keys from Redis.

    Accepts redis key-pattern for narrowing down the list of items to
    remove. By default removes everything.

    This fixture removes all the records from Redis on call::

        def test_redis_is_empty(reset_redis):
            redis = connect_to_redis()
            redis.set("test", "test")

            reset_redis()
            assert not redis.get("test")

    If only specific records require removal, pass a pattern to the fixture::

        def test_redis_is_empty(reset_redis):
            redis = connect_to_redis()
            redis.set("AAA-1", 1)
            redis.set("AAA-2", 2)
            redis.set("BBB-3", 3)

            reset_redis("AAA-*")
            assert not redis.get("AAA-1")
            assert not redis.get("AAA-2")

            assert redis.get("BBB-3") is not None

    """
    def cleaner(pattern: str = "*") -> int:
        """Remove keys matching pattern.

        Return number of removed records.
        """
        conn = redis.connect_to_redis()
        keys = conn.keys(pattern)
        if keys:
            return conn.delete(*keys)  # type: ignore
        return 0

    return cleaner


@pytest.fixture()
def clean_redis(reset_redis: types.FixtureResetRedis):
    """Remove all keys from Redis.

    This fixture removes all the records from Redis::

        @pytest.mark.usefixtures("clean_redis")
        def test_redis_is_empty():
            assert redis.keys("*") == []

    If test requires presence of some initial data in redis, make sure that
    data producer applied **after** ``clean_redis``::

        @pytest.mark.usefixtures(
            "clean_redis",
            "fixture_that_adds_xxx_key_to_redis"
        )
        def test_redis_has_one_record():
            assert redis.keys("*") == [b"xxx"]

    """
    reset_redis()


@pytest.fixture
def clean_db(reset_db: types.FixtureResetDb):
    """Resets the database to the initial state.

    This can be used either for all tests in a class::

        @pytest.mark.usefixtures("clean_db")
        class TestExample(object):

            def test_example(self):

    or for a single test::

        class TestExample(object):

            @pytest.mark.usefixtures("clean_db")
            def test_example(self):

    """
    reset_db()


@pytest.fixture
def clean_queues(reset_queues: types.FixtureResetQueues):
    """Empties and deleted all queues.

    This can be used either for all tests in a class::

        @pytest.mark.usefixtures("clean_queues")
        class TestExample(object):

            def test_example(self):

    or for a single test::

        class TestExample(object):

            @pytest.mark.usefixtures("clean_queues")
            def test_example(self):

    """
    reset_queues()


@pytest.fixture(scope="session")
def migrate_db_for():
    """Apply database migration defined by plugin.

    In order to use models defined by extension extra tables may be
    required. In such cases database migrations(that were generated by `ckan
    generate migration -p PLUGIN_NAME`) can be applied as per example below::

        @pytest.mark.usefixtures("clean_db")
        def test_migrations_applied(migrate_db_for):
            migrate_db_for("my_plugin")
            assert model.Session.bind.has_table("my_plugin_custom_table")

    """
    from ckan.cli.db import _run_migrations

    def runner(plugin: str, version: str = "head", forward: bool = True):
        assert plugin, "Cannot apply migrations of unknown plugin"
        _run_migrations(plugin, version, forward)

    return runner


@pytest.fixture
def clean_index(reset_index: types.FixtureResetIndex):
    """Clear search index before starting the test.
    """
    reset_index()


@pytest.fixture
def provide_plugin(
    request: pytest.FixtureRequest,
) -> Iterable[Callable[[str, type], Any]]:
    """Register CKAN plugins during test execution.

    This fixture can be used inside test to register a new plugin::

        def test_fake_plugin(provide_plugin):
            provide_plugin("list_plugin", list)
            assert plugins.load("list_plugin") == []

    Alternatively, test plugins can be added with `provide_plugin` mark, which
    inernally relies on the current fixture::

        @pytest.mark.provide_plugin("list_plugin", list)
        @pytest.mark.ckan_config("ckan.plugins", "list_plugin")
        @pytest.mark.usefixtures("with_plugins")
        def test_fake_plugin():
            plugin = plugins.get_plugin("list_plugin")
            assert  plugin == []

    The last example can be rewritten using mark `with_plugins`, which applies
    `provide_plugin` all its dict-arguments::

        @pytest.mark.with_plugins({"list_plugin": list})
        def test_fake_plugin():
            plugin = plugins.get_plugin("list_plugin")
            assert  plugin == []

    """
    from ckan.plugins.core import _get_service

    markers = cast(
        "list[pytest.Mark]",
        request.node.iter_markers("provide_plugin"),
    )
    plugins: dict[str, type] = dict(mark.args for mark in markers)

    plugin_maker = mock.Mock(
        side_effect=lambda name: plugins[name]() if name in plugins else mock.DEFAULT,
        wraps=_get_service,
    )
    with mock.patch("ckan.plugins.core._get_service", plugin_maker):
        yield lambda name, plugin: plugins.update({name: plugin})


@pytest.fixture
def with_plugins(
    ckan_config: types.FixtureCkanConfig,
    provide_plugin: types.FixtureProvidePlugin,
    monkeypatch: pytest.MonkeyPatch,
    request: pytest.FixtureRequest,
):
    """Load all plugins specified by the ``ckan.plugins`` config option at the
    beginning of the test(and disable any plugin which is not listed inside
    ``ckan.plugins``). When the test ends (including fail), it will unload all
    the plugins.

    .. literalinclude:: /../ckan/tests/test_factories.py
       :start-after: # START-CONFIG-OVERRIDE
       :end-before: # END-CONFIG-OVERRIDE

    Use this fixture if test relies on CKAN plugin infrastructure. For example,
    if test calls an action or helper registered by plugin XXX::

        @pytest.mark.ckan_config("ckan.plugins", "XXX")
        @pytest.mark.usefixtures("with_plugin")
        def test_action_and_helper():
            assert call_action("xxx_action")
            assert tk.h.xxx_helper()

    It will not work without ``with_plugins``. If ``XXX`` plugin is not loaded,
    ``xxx_action`` and ``xxx_helper`` do not exist in CKAN registries.

    But if the test above use direct imports instead, ``with_plugins`` is
    optional::

        def test_action_and_helper():
            from ckanext.xxx.logic.action import xxx_action
            from ckanext.xxx.helpers import xxx_helper

            assert xxx_action()
            assert xxx_helper()

    Keep in mind, that generally it's a bad idea to import helpers and actions
    directly. If **every** test of extension requires standard set of plugins,
    specify these plugins inside test config file(``test.ini``)::

        ckan.plugins = essential_plugin another_plugin_required_by_every_test

    And create an autouse-fixture that depends on ``with_plugins`` inside
    the main ``conftest.py`` (``ckanext/ext/tests/conftest.py``)::

        @pytest.fixture(autouse=True)
        def load_standard_plugins(with_plugins):
            ...

    This will automatically enable ``with_plugins`` for every test, even if
    it's not required explicitely.

    The fixture can be used as mark. It iterates over all arguments and appends
    them to the list of ``ckan.plugins`` before loading. This can be used to
    enable few plugins **in addition** to any plugins that are already
    specified by the ``ckan.plugins`` option::

        @pytest.mark.with_plugins("XXX", "YYY")
        def test_action_and_helper():
            assert plugins.plugin_loaded("XXX")
            assert plugins.plugin_loaded("XXX")
            # any other plugin from `ckan.plugins` is loaded as well

    """
    markers = cast(
        "list[pytest.Mark]",
        request.node.iter_markers("with_plugins"),
    )
    plugins = itertools.chain.from_iterable(mark.args for mark in markers)

    names = []
    for plugin in plugins:
        if isinstance(plugin, str):
            names.append(plugin)
        elif isinstance(plugin, dict):
            for name, impl in plugin.items():
                provide_plugin(name, impl)
                names.append(name)
        else:
            assert False, f"Unexpectedd argument {plugin} for with_plugins mark"

    current_plugins: str | list[str] = ckan_config["ckan.plugins"]
    if isinstance(current_plugins, str):
        current_plugins = current_plugins.split()

    monkeypatch.setitem(ckan_config, "ckan.plugins", current_plugins + names)

    ckan.plugins.load_all()
    yield
    ckan.plugins.unload_all()


@pytest.fixture
def test_request_context(app: types.FixtureApp) -> types.RequestContext:
    """Provide function for creating Flask request context.
    """
    return app.flask_app.test_request_context


@pytest.fixture
def with_request_context(test_request_context: types.FixtureTestRequestContext):
    """Execute test inside requests context
    """
    with test_request_context():
        yield


@pytest.fixture
def mail_server(monkeypatch: pytest.MonkeyPatch):
    """Catch all outcome mails.
    """
    bag = test_helpers.FakeSMTP()
    monkeypatch.setattr(smtplib, u"SMTP", bag)
    yield bag


@pytest.fixture
def with_test_worker(monkeypatch: pytest.MonkeyPatch):
    """Worker that doesn't create forks.
    """
    monkeypatch.setattr(
        rq.Worker, u"main_work_horse", rq.SimpleWorker.main_work_horse
    )
    monkeypatch.setattr(
        rq.Worker, u"execute_job", rq.SimpleWorker.execute_job
    )
    yield


@pytest.fixture
def with_extended_cli(
        ckan_config: types.FixtureCkanConfig,
        monkeypatch: pytest.MonkeyPatch,
):
    """Enables effects of IClick.

    Without this fixture, only CLI command that came from plugins
    specified in real config file are available. When this fixture
    enabled, changing `ckan.plugins` on test level allows to update
    list of available CLI command.

    """
    # Main `ckan` command is initialized from config file instead of
    # using global config object.  With this patch it becomes possible
    # to apply per-test config changes to it without creating real
    # config file.
    monkeypatch.setattr(ckan.cli, u"load_config", lambda _: ckan_config)


@pytest.fixture(scope="session")
def reset_db_once(reset_db: types.FixtureResetDb):
    """Internal fixture that cleans DB only the first time it's used.
    """
    reset_db()


@pytest.fixture
def non_clean_db(reset_db_once: types.FixtureResetDb):
    """Guarantees that DB is initialized.

    This fixture either initializes DB if it hasn't been done yet or does
    nothing otherwise. If there is some data in DB, it stays intact. If your
    tests need empty database, use `clean_db` instead, which is much slower,
    but guarantees that there are no data left from the previous test session.

    Example::

        @pytest.mark.usefixtures("non_clean_db")
        def test_example():
            assert factories.User()

    """
    model.repo.init_db()


class FakeFileStorage(FlaskFileStorage):
    def __init__(self, stream: IO[bytes], filename: str):
        super(FakeFileStorage, self).__init__(stream, filename, "uplod")


@pytest.fixture
def create_with_upload(
        clean_db: None,
        ckan_config: types.FixtureCkanConfig,
        monkeypatch: pytest.MonkeyPatch,
        tmpdir: Any,
):
    """Shortcut for creating resource/user/org with upload.

    Requires content and name for newly created object. By default is
    using `resource_create` action, but it can be changed by passing
    named argument `action`.

    Upload field if configured by passing `upload_field_name` named
    argument. Default value: `upload`.

    In addition, accepts named argument `context` which will be passed
    to `ckan.tests.helpers.call_action` and arbitrary number of
    additional named arguments, that will be used as resource
    properties.

    Example::

        def test_uploaded_resource(create_with_upload):
            dataset = factories.Dataset()
            resource = create_with_upload(
                "hello world", "file.txt", url="http://data",
                package_id=dataset["id"])
            assert resource["url_type"] == "upload"
            assert resource["format"] == "TXT"
            assert resource["size"] == 11

    """
    monkeypatch.setitem(ckan_config, u'ckan.storage_path', str(tmpdir))

    def factory(
            data: str | bytes,
            filename: str,
            context: types.Context | None = None,
            **kwargs: Any
    ):
        if context is None:
            context = {}
        action = kwargs.pop("action", "resource_create")
        field = kwargs.pop("upload_field_name", "upload")
        test_file = BytesIO()
        if isinstance(data, str):
            data = bytes(data, encoding="utf-8")
        test_file.write(data)
        test_file.seek(0)
        test_resource = FakeFileStorage(test_file, filename)

        params = {
            field: test_resource,
        }
        params.update(kwargs)
        return test_helpers.call_action(action, context, **params)
    return factory
