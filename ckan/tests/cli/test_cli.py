# -*- coding: utf-8 -*-

from configparser import InterpolationMissingOptionError
import pytest
import os

from ckan.cli.cli import ckan
from ckan.cli import CKANConfigLoader
from ckan.exceptions import CkanConfigurationException


def test_without_args(cli):
    """Show help by default.
    """
    result = cli.invoke(ckan)
    assert 'Usage: ckan' in result.output
    assert not result.exit_code


def test_incorrect_config(cli):
    """Config file must exist.
    """
    result = cli.invoke(ckan, ['-c', '/a/b/c/d/e/f/g/h.ini'])
    assert result.output.startswith('Config file not found')


def test_correct_config(cli, ckan_config):
    """With explicit config file user still sees help message.
    """
    result = cli.invoke(ckan, ['-c', ckan_config['__file__']])
    assert 'Usage: ckan' in result.output
    assert not result.exit_code


def test_correct_config_with_help(cli, ckan_config):
    """Config file not ignored when displaying usage.
    """
    result = cli.invoke(ckan, ['-c', ckan_config['__file__'], '-h'])
    assert not result.exit_code


def test_config_via_env_var(cli, ckan_config):
    """CliRunner uses test config automatically, so we have to explicitly
    set CLI `-c` option to `None` when using env `CKAN_INI`.

    """
    result = cli.invoke(ckan, ['-c', None, '-h'],
                        env={'CKAN_INI': ckan_config['__file__']})
    assert not result.exit_code


@pytest.mark.ckan_config('ckan.plugins', 'example_iclick')
@pytest.mark.usefixtures('with_plugins', 'with_extended_cli')
def test_command_from_extension_shown_in_help_when_enabled(cli):
    """Extra commands shown in help when plugin enabled.
    """
    result = cli.invoke(ckan, [])
    assert 'example-iclick-hello' in result.output

    result = cli.invoke(ckan, ['--help'])
    assert 'example-iclick-hello' in result.output


def test_ckan_config_loader_parse_file():
    """
    CKANConfigLoader should parse and interpolate variables in
    test-core.ini.tpl file both in DEFAULT and app:main section.
    """
    tpl_dir = os.path.dirname(__file__) + '/templates'
    filename = os.path.join(tpl_dir, 'test-core.ini.tpl')
    conf = CKANConfigLoader(filename).get_config()

    assert conf['debug'] == 'false'

    assert conf['key1'] == tpl_dir + '/core'
    assert conf['key2'] == tpl_dir + '/core'
    assert conf['key4'] == 'core'

    assert conf['__file__'] == filename

    with pytest.raises(KeyError):
        conf['host']

    assert conf['global_conf']['__file__'] == filename
    assert conf['global_conf']['here'] == tpl_dir
    assert conf['global_conf']['debug'] == 'false'


def test_ckan_config_loader_parse_two_files():
    """
    CKANConfigLoader should parse both 'test-extension.ini.tpl' and
    'test-core.ini.tpl' and override the values of 'test-core.ini.tpl' with
    the values of test-extension.ini.tpl.

    Values in [DEFAULT] section are always override.
    """
    tpl_dir = os.path.dirname(__file__) + '/templates'
    extension_tpl_dir = tpl_dir + '/ckanext-extension'
    filename = os.path.join(extension_tpl_dir, 'test-extension.ini.tpl')
    conf = CKANConfigLoader(filename).get_config()

    # Debug should be override by test-core.ini.tpl since is in DEFAULT section
    assert conf['debug'] == 'false'
    # __file__ should never be override if parsing two files
    assert conf['__file__'] == filename

    assert conf['key1'] == extension_tpl_dir + '/extension'
    assert conf['key2'] == tpl_dir + '/core'
    assert conf['key3'] == extension_tpl_dir + '/extension'
    assert conf['key4'] == 'extension'

    with pytest.raises(KeyError):
        conf['host']

    assert conf['global_conf']['__file__'] == filename
    assert conf['global_conf']['here'] == tpl_dir
    assert conf['global_conf']['debug'] == 'false'


def test_ckan_env_vars_in_config(monkeypatch):
    """CKAN_ prefixed environment variables can be used in config.
    """
    filename = os.path.join(
        os.path.dirname(__file__), 'data', 'test-env-var.ini')
    monkeypatch.setenv("CKAN_TEST_ENV_VAR", "value")
    conf = CKANConfigLoader(filename).get_config()
    assert conf["var"] == "value"


def test_other_env_vars_ignored(monkeypatch):
    """Non-CKAN_ environment variables are ignored
    """
    filename = os.path.join(
        os.path.dirname(__file__), 'data', 'test-no-env-var.ini')
    monkeypatch.setenv("TEST_ENV_VAR", "value")
    with pytest.raises(InterpolationMissingOptionError):
        CKANConfigLoader(filename).get_config()


def test_chain_loading():
    """Load chains of config files via `use = config:...`.
    """
    filename = os.path.join(
        os.path.dirname(__file__), 'data', 'test-one.ini')
    conf = CKANConfigLoader(filename).get_config()
    assert conf['__file__'] == filename
    assert conf['key1'] == 'one'
    assert conf['key2'] == 'two'
    assert conf['key3'] == 'three'


def test_recursive_loading():
    """ Make sure we still remember main config file.

    If there are circular dependencies, make sure the user knows about it.
    """
    filename = os.path.join(
        os.path.dirname(__file__), 'data', 'test-one-recursive.ini')
    with pytest.raises(CkanConfigurationException):
        CKANConfigLoader(filename).get_config()
