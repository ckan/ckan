# -*- coding: utf-8 -*-

import pytest
import os

from ckan.cli.cli import ckan
from ckan.cli import CKANConfigLoader


def test_without_args(cli):
    """Show help by default.
    """
    result = cli.invoke(ckan)
    assert u'Usage: ckan' in result.output
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


@pytest.mark.ckan_config(u'ckan.plugins', u'example_iclick')
@pytest.mark.usefixtures(u'with_plugins', u'with_extended_cli')
def test_command_from_extension_shown_in_help_when_enabled(cli):
    """Extra commands shown in help when plugin enabled.
    """
    result = cli.invoke(ckan, [])
    assert u'example-iclick-hello' in result.output


def test_ckan_config_loader_parse_file():
    """
    CKANConfigLoader should parse and interpolate variables in
    test-core.ini.tpl file both in DEFAULT and app:main section.
    """
    tpl_dir = os.path.dirname(__file__) + u'/templates'
    filename = os.path.join(tpl_dir, u'test-core.ini.tpl')
    conf = CKANConfigLoader(filename).get_config()

    assert conf[u'debug'] == u'false'

    assert conf[u'key1'] == tpl_dir + u'/core'
    assert conf[u'key2'] == tpl_dir + u'/core'
    assert conf[u'key4'] == u'core'

    assert conf[u'__file__'] == filename

    with pytest.raises(KeyError):
        conf[u'host']

    assert conf[u'global_conf'][u'__file__'] == filename
    assert conf[u'global_conf'][u'here'] == tpl_dir
    assert conf[u'global_conf'][u'debug'] == u'false'


def test_ckan_config_loader_parse_two_files():
    """
    CKANConfigLoader should parse both 'test-extension.ini.tpl' and
    'test-core.ini.tpl' and override the values of 'test-core.ini.tpl' with
    the values of test-extension.ini.tpl.

    Values in [DEFAULT] section are always override.
    """
    tpl_dir = os.path.dirname(__file__) + u'/templates'
    extension_tpl_dir = tpl_dir + u'/ckanext-extension'
    filename = os.path.join(extension_tpl_dir, u'test-extension.ini.tpl')
    conf = CKANConfigLoader(filename).get_config()

    # Debug should be override by test-core.ini.tpl since is in DEFAULT section
    assert conf[u'debug'] == u'false'
    # __file__ should never be override if parsing two files
    assert conf[u'__file__'] == filename

    assert conf[u'key1'] == extension_tpl_dir + u'/extension'
    assert conf[u'key2'] == tpl_dir + u'/core'
    assert conf[u'key3'] == extension_tpl_dir + u'/extension'
    assert conf[u'key4'] == u'extension'

    with pytest.raises(KeyError):
        conf[u'host']

    assert conf[u'global_conf'][u'__file__'] == filename
    assert conf[u'global_conf'][u'here'] == tpl_dir
    assert conf[u'global_conf'][u'debug'] == u'false'
