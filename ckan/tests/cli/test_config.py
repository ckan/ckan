# -*- coding: utf-8 -*-

import unittest.mock as mock
import pytest

from werkzeug.utils import import_string

from ckan.cli.cli import ckan


@pytest.fixture
def command(cli):
    def invoke(*args):
        return cli.invoke(ckan, ("config",) + args)

    return invoke


@pytest.mark.usefixtures("with_extended_cli")
@pytest.mark.ckan_config("config.mode", "strict")
class TestDescribe(object):
    def test_basic_invocation(self, command):
        """Command prints nothing without arguments;"""
        result = command("describe")
        assert not result.output
        assert not result.exit_code, result.output

    @pytest.mark.ckan_config(u"ckan.plugins", u"datastore")
    @pytest.mark.usefixtures("with_plugins")
    def test_enabled(self, command):
        """Can list configuration from the enabled plugins."""
        result = command("describe", "--enabled")
        assert "Datastore settings" in result.output
        assert not result.exit_code, result.output

    def test_core(self, command):
        """Can show core declarations."""
        result = command("describe", "--core")
        assert "Database settings" in result.output
        assert not result.exit_code, result.output

    def test_explicit(self, command):
        """Can list disabled plugins with explicit argument"""
        result = command("describe", "datastore")
        assert "Datastore settings" in result.output
        assert not result.exit_code, result.output

    @pytest.mark.parametrize(
        "fmt, loader",
        [
            ("yaml", "yaml:safe_load"),
            ("dict", "builtins:eval"),
            ("json", "json:loads"),
            ("toml", "toml:loads"),
        ],
    )
    def test_formats(self, fmt, loader, command):
        """Can export declaration into different formats."""
        load = import_string(loader)
        result = command("describe", "datapusher", "--format", fmt)
        data = load(result.output)

        assert data == {
            "version": 1,
            "groups": [
                {
                    "annotation": "Datapusher settings",
                    "options": [
                        {
                            "key": "ckan.datapusher.formats",
                            "default": [
                                "csv",
                                "xls",
                                "xlsx",
                                "tsv",
                                "application/csv",
                                "application/vnd.ms-excel",
                                "application/vnd.openxmlformats-officedocument"
                                ".spreadsheetml.sheet",
                                "ods",
                                "application/vnd.oasis.opendocument"
                                ".spreadsheet",
                            ],
                            "validators": "as_list",
                            "description": mock.ANY,
                        },
                        {
                            "key": "ckan.datapusher.url",
                            "description": mock.ANY,
                        },
                        {
                            "key": "ckan.datapusher.api_token",
                            "description": mock.ANY,
                        },

                        {
                            "key": "ckan.datapusher.callback_url_base",
                            "description": mock.ANY,
                            "placeholder": "%(ckan.site_url)s",
                        },
                        {
                            "key": "ckan.datapusher.assume_task_stale_after",
                            "default": 3600,
                            "validators": "convert_int",
                            "description": mock.ANY,
                        },
                    ],
                }
            ],
        }, data


@pytest.mark.usefixtures("with_extended_cli")
@pytest.mark.ckan_config("config.mode", "strict")
class TestDeclaration(object):
    def test_basic_invocation(self, command):
        result = command("declaration")
        assert not result.output
        assert not result.exit_code, result.output

    def test_core(self, command):
        result = command("declaration", "--core")
        assert result.output.startswith("\n## General settings ##")
        assert not result.exit_code, result.output

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("with_plugins")
    def test_enabled(self, command):
        result = command("declaration", "--enabled")
        assert "Datastore settings" in result.output
        assert (
            "ckan.datastore.write_url ="
            " postgresql://ckan_default:pass@localhost/datastore_default"
            in result.output
        )

        assert not result.exit_code, result.output

    def test_explicit(self, command):
        result = command("declaration", "datastore")
        assert "Datastore settings" in result.output
        assert (
            "ckan.datastore.write_url ="
            " postgresql://ckan_default:pass@localhost/datastore_default"
            in result.output
        )
        assert not result.exit_code, result.output


@pytest.mark.usefixtures("with_extended_cli")
@pytest.mark.ckan_config("config.mode", "strict")
class TestSearch(object):
    def test_wrong_non_pattern(self, command):
        result = command("search", "ckan")
        assert not result.output
        assert not result.exit_code, result.output

    def test_valid_non_pattern(self, command):
        result = command("search", "use")
        assert result.output == "use\n"
        assert not result.exit_code, result.output

    def test_non_existing_pattern(self, command):
        result = command("search", "not-exist.*")
        assert not result.output
        assert not result.exit_code, result.output

    def test_existing_pattern(self, command):
        result = command("search", "sqlalchemy.*")
        assert "sqlalchemy.url" in result.output
        assert not result.exit_code, result.output

    @pytest.mark.ckan_config("ckan.plugins", "")
    @pytest.mark.usefixtures("with_plugins")
    def test_disabled_plugin_pattern(self, command):
        result = command("search", "ckan.datastore.*")
        assert "datastore.read_url" not in result.output
        assert not result.exit_code, result.output

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("with_plugins")
    def test_enabled_plugin_pattern(self, command):
        result = command("search", "ckan.datastore.*")
        assert "datastore.read_url" in result.output
        assert not result.exit_code, result.output

    @pytest.mark.ckan_config("ckan.plugins", "")
    @pytest.mark.usefixtures("with_plugins")
    def test_extra_plugin_pattern(self, command):
        result = command(
            "search", "ckan.datastore.*", "--include-plugin", "datastore"
        )
        assert "datastore.read_url" in result.output
        assert not result.exit_code, result.output


@pytest.mark.usefixtures("with_extended_cli")
@pytest.mark.ckan_config("config.mode", "strict")
class TestUndeclared(object):
    def test_no_undeclared_options_by_default(self, command):
        result = command("undeclared", "-idatapusher", "-idatastore")
        assert not result.output
        assert not result.exit_code, result.output

    @pytest.mark.ckan_config("ckan.resource_proxy.max_file_size", 10)
    def test_report_undeclared(self, command):
        result = command("undeclared", "-idatapusher", "-idatastore")
        assert "ckan.resource_proxy.max_file_size" in result.output
        assert not result.exit_code, result.output

    @pytest.mark.ckan_config("sqlalchemy.echo", False)
    @pytest.mark.ckan_config("sqlalchemy-wrong", 3)
    def test_allow_dynamic_groups(self, command):
        result = command("undeclared", "-idatapusher", "-idatastore")
        assert "sqlalchemy.echo" not in result.output
        assert "sqlalchemy-wrong" in result.output
        assert not result.exit_code, result.output

    @pytest.mark.ckan_config("ckan.resource_proxy.max_file_size", 10)
    @pytest.mark.ckan_config("ckan.plugins", "resource_proxy")
    @pytest.mark.usefixtures("with_plugins")
    def test_ignore_declared(self, command):
        result = command("undeclared", "-idatapusher", "-idatastore")
        assert not result.output
        assert not result.exit_code, result.output


@pytest.mark.usefixtures("with_extended_cli")
class TestValidate(object):
    def test_no_errors_by_default_in_safe_mofe(self, command):
        result = command("validate")
        assert not result.output
        assert not result.exit_code, result.output

    @pytest.mark.ckan_config("ckan.devserver.port", "8-thousand")
    def test_invalid_port(self, command):
        result = command("validate")
        assert not result.exit_code, result.output
        assert "ckan.devserver.port" in result.stdout

    @pytest.mark.ckan_config("config.mode", "strict")
    @pytest.mark.ckan_config("ckan.devserver.port", "8-thousand")
    def test_invalid_port_in_strict_mode_prevents_application_initialization(self, command):
        result = command("validate")
        assert result.exit_code, result.stdout
