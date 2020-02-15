# -*- coding: utf-8 -*-

import pytest
import os

from ckan.cli.cli import ckan
from ckan.cli import CKANConfigLoader


def test_without_args(cli):
    """Show help by default.
    """
    result = cli.invoke(ckan)
    assert result.output.startswith(u'Usage: ckan')
    assert not result.exit_code


def test_incorrect_config(cli):
    """Config file must exist.
    """
    result = cli.invoke(ckan, [u'-c', u'/a/b/c/d/e/f/g/h.ini'])
    assert result.output.startswith(u'Config file not found')


def test_correct_config(cli, ckan_config):
    """Presense of config file disables default printing of help message.
    """
    result = cli.invoke(ckan, [u'-c', ckan_config[u'__file__']])
    assert u'Error: Missing command.' in result.output
    assert result.exit_code


def test_correct_config_with_help(cli, ckan_config):
    """Config file not ignored when displaying usage.
    """
    result = cli.invoke(ckan, [u'-c', ckan_config[u'__file__'], u'-h'])
    assert not result.exit_code


def test_config_via_env_var(cli, ckan_config):
    """CliRunner uses test config automatically, so we have to explicitly
    set CLI `-c` option to `None` when using env `CKAN_INI`.

    """
    result = cli.invoke(ckan, [u'-c', None, u'-h'],
                        env={u'CKAN_INI': ckan_config[u'__file__']})
    assert not result.exit_code


def test_command_from_extension_is_not_available_without_extension(cli):
    """Extension must be enabled in order to make its commands available.
    """
    result = cli.invoke(ckan, [u'example-iclick-hello'])
    assert result.exit_code


@pytest.mark.ckan_config(u'ckan.plugins', u'example_iclick')
@pytest.mark.usefixtures(u'with_plugins')
def test_command_from_extension_is_not_available_without_additional_fixture(cli):
    """Without `with_extended_cli` extension still unable to register
    command durint tests.

    """
    result = cli.invoke(ckan, [u'example-iclick-hello'])
    assert result.exit_code


@pytest.mark.ckan_config(u'ckan.plugins', u'example_iclick')
@pytest.mark.usefixtures(u'with_plugins', u'with_extended_cli')
def test_command_from_extension_is_available_when_all_requirements_satisfied(cli):
    """When enabled, extension register its CLI commands.
    """
    result = cli.invoke(ckan, [u'example-iclick-hello'])
    assert not result.exit_code


def test_ckan_config_loader_parse_file():
    """
    CKANConfigLoader should parse and interpolate variables in
    test-core.ini.tpl file both in DEFAULT and app:main section.
    """
    data_dir = os.path.dirname(__file__) + u'/data/'
    filename = os.path.join(data_dir, u'test-core.ini.tpl')
    conf = CKANConfigLoader(filename).get_config()

    assert conf[u'debug'] == u'false'

    assert conf[u'key1'] == data_dir + u'core'
    assert conf[u'key2'] == data_dir + u'core'
    assert conf[u'key4'] == u'core'

    with pytest.raises(KeyError):
        conf[u'host']


def test_ckan_config_loader_parse_two_files():
    """
    CKANConfigLoader should parse both 'test-extension.ini.tpl' and
    'test-core.ini.tpl' and override the values of 'test-core.ini.tpl' with
    the values of test-extension.ini.tpl.
    """
    data_dir = os.path.dirname(__file__) + u'/data/'
    extension_data_dir = data_dir + u'ckanext-extension/'

    filename = os.path.join(extension_data_dir, u'test-extension.ini.tpl')
    conf = CKANConfigLoader(filename).get_config()

    assert conf[u'debug'] == u'false'

    assert conf[u'key1'] == extension_data_dir + u'extension'
    assert conf[u'key2'] == data_dir + u'core'
    assert conf[u'key3'] == extension_data_dir + u'extension'
    assert conf[u'key4'] == u'extension'

    with pytest.raises(KeyError):
        conf[u'host']


def test_here_config_is_evaluated_on_each_inherit_file():
    file = u'data/ckanext-extension/test-extension.ini.tpl'
    filename = os.path.join(os.path.dirname(__file__), file)
    conf = CKANConfigLoader(filename).get_config()

    data_dir = os.path.join(os.path.dirname(__file__), u'data')
    assert conf[u'here'] == data_dir


def test_file_config_is_not_evaluated_on_each_inherit_file():
    file = u'data/ckanext-extension/test-extension.ini.tpl'
    filename = os.path.join(os.path.dirname(__file__), file)
    conf = CKANConfigLoader(filename).get_config()

    assert conf[u'__file__'] == filename


def test_global_conf_key_is_set_properly_reading_one_file():
    """
    This test is for compatibility with Pylons stack. Can be safely removed
    when the migration to Flask is completed.
    """
    file = u'data/test-core.ini.tpl'
    data_dir = os.path.join(os.path.dirname(__file__), u'data')
    filename = os.path.join(os.path.dirname(__file__), file)
    conf = CKANConfigLoader(filename).get_config()

    assert conf[u'global_conf'][u'__file__'] == filename
    assert conf[u'global_conf'][u'here'] == data_dir
    assert conf[u'global_conf'][u'debug'] == u'false'


def test_global_conf_key_is_set_properly_reading_two_files():
    """
    This test is for compatibility with Pylons stack. Can be safely removed
    when the migration to Flask is completed.
    """
    data_dir = os.path.join(os.path.dirname(__file__), u'data')

    file = u'data/ckanext-extension/test-extension.ini.tpl'
    filename = os.path.join(os.path.dirname(__file__), file)
    conf = CKANConfigLoader(filename).get_config()

    assert conf[u'global_conf'][u'__file__'] == filename
    assert conf[u'global_conf'][u'here'] == data_dir
    assert conf[u'global_conf'][u'debug'] == u'false'


def test_default_confs_are_evaluated_on_each_inherit_file():
    """
    This test is for compatibility with Pylons stack. Can be safely removed
    when the migration to Flask is completed.
    """
    data_dir = os.path.join(os.path.dirname(__file__), u'data')

    file = u'data/ckanext-extension/test-extension.ini.tpl'
    filename = os.path.join(os.path.dirname(__file__), file)
    conf = CKANConfigLoader(filename).get_config()

    assert conf[u'debug'] == u'false'
