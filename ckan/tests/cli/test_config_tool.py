# -*- coding: utf-8 -*-

import os
import pytest
from ckan.cli.cli import ckan
from six.moves.configparser import ConfigParser, NoOptionError


@pytest.fixture
def config_file(tmp_path):
    dest = tmp_path / 'config.ini'
    tpl = os.path.join(
        os.path.dirname(__file__),
        'templates/config_tool.ini.tpl')
    with open(tpl, 'rb') as data:
        dest.write_bytes(data.read())
    return dest


def _parse(config_file):
    parser = ConfigParser()
    parser.read([str(config_file)])
    return parser


def test_config_no_params(cli, config_file):
    """test-config requires some params for update.
    """
    result = cli.invoke(ckan, ['config-tool', str(config_file)])
    assert result.exit_code


def test_config_unset_debug(cli, config_file):
    """Existing values can be updated.
    """
    assert _parse(config_file).get('app:main', 'debug') == 'true'
    result = cli.invoke(
        ckan,
        ['config-tool', str(config_file), 'debug=false']

    )
    assert not result.exit_code
    assert _parse(config_file).get('app:main', 'debug') == 'false'


def test_config_create_custom_debug(cli, config_file):
    """New values can be added
    """
    with pytest.raises(NoOptionError):
        _parse(config_file).get('app:main', 'custom_debug')
    result = cli.invoke(
        ckan, ['config-tool',
               str(config_file), 'custom_debug=false'])
    assert not result.exit_code
    assert _parse(config_file).get('app:main', 'custom_debug') == 'false'


def test_config_custom_section(cli, config_file):
    """Custom section updated when specified.
    """
    assert _parse(config_file).get('server:main', 'port') == '5000'
    result = cli.invoke(ckan, [
        'config-tool',
        str(config_file), '-s', 'server:main', 'port=8000'
    ])
    assert not result.exit_code
    assert _parse(config_file).get('server:main', 'port') == '8000'


def test_merge_into_new_file(cli, config_file, tmp_path):
    """New file can be created without updating old one.
    """
    dest = tmp_path / 'new_config.ini'
    dest.touch()
    assert _parse(config_file).get('app:main', 'debug') == 'true'
    result = cli.invoke(
        ckan,
        ['config-tool',
         str(dest), '-f',
         str(config_file), 'debug=false'])
    assert not result.exit_code
    assert _parse(config_file).get('app:main', 'debug') == 'true'
    assert _parse(dest).get('app:main', 'debug') == 'false'
