# -*- coding: utf-8 -*-

import pytest

import ckan.authz as authz
from ckan.cli.cli import ckan as ckan_command
from ckan.logic import get_action, get_validator, UnknownValidator
from ckan.lib.helpers import helper_functions as h


@pytest.mark.usefixtures(u"with_plugins", u"with_extended_cli")
class TestBlanketImplementation(object):
    def _helpers_registered(self):
        try:
            h.bed()
            h.pillow()
            h.blanket_helper()
        except AttributeError:
            return False
        with pytest.raises(AttributeError):
            h._hidden_helper()
        with pytest.raises(AttributeError):
            h.randrange(1, 10)
        return True

    def _auth_registered(self):
        functions = authz.auth_functions_list()
        return u'sleep' in functions and u'wake_up' in functions

    def _actions_registered(self):
        try:
            get_action(u'sleep')
            get_action(u'wake_up')
        except KeyError:
            return False
        return True

    def _blueprints_registered(self, app):
        return u'blanket' in app.flask_app.blueprints

    def _commands_registered(self, cli):
        result = cli.invoke(ckan_command, [u'blanket'])
        return not result.exit_code

    def _validators_registered(self):
        try:
            get_validator(u'is_blanket')
        except UnknownValidator:
            return False
        return True

    def _config_declarations_registered(self, config):
        return config.get("ckanext.blanket") == "declaration blanket"

    @pytest.mark.ckan_config(u"ckan.plugins", u"example_blanket")
    def test_empty_blanket_implements_all_available_interfaces(self, app, cli, ckan_config):
        """When applied with no arguments, search through default files and
        apply interfaces whenever is possible.

        """
        assert self._helpers_registered()
        assert self._auth_registered()
        assert self._actions_registered()
        assert self._blueprints_registered(app)
        assert self._commands_registered(cli)
        assert self._validators_registered()
        assert self._config_declarations_registered(ckan_config)

    @pytest.mark.ckan_config(u"ckan.plugins", u"example_blanket_helper")
    def test_blanket_default(self, app, cli, ckan_config):
        """If only type provided, register default file as dictionary.
        """
        assert self._helpers_registered()
        assert not self._auth_registered()
        assert not self._actions_registered()
        assert not self._blueprints_registered(app)
        assert not self._commands_registered(cli)
        assert not self._validators_registered()
        assert not self._config_declarations_registered(ckan_config)

    @pytest.mark.ckan_config(u"ckan.plugins", u"example_blanket_auth")
    def test_blanket_module(self, app, cli, ckan_config):
        """If module provided as subject, register __all__ as dictionary.
        """
        assert not self._helpers_registered()
        assert self._auth_registered()
        assert not self._actions_registered()
        assert not self._blueprints_registered(app)
        assert not self._commands_registered(cli)
        assert not self._validators_registered()
        assert not self._config_declarations_registered(ckan_config)

    @pytest.mark.ckan_config(u"ckan.plugins", u"example_blanket_action")
    def test_blanket_function(self, app, cli, ckan_config):
        """If function provided as subject, register its result.
        """
        assert not self._helpers_registered()
        assert not self._auth_registered()
        assert self._actions_registered()
        assert not self._blueprints_registered(app)
        assert not self._commands_registered(cli)
        assert not self._validators_registered()
        assert not self._config_declarations_registered(ckan_config)

    @pytest.mark.ckan_config(u"ckan.plugins", u"example_blanket_blueprint")
    def test_blanket_lambda(self, app, cli, ckan_config):
        """If lambda provided as subject, register its result.
        """
        assert not self._helpers_registered()
        assert not self._auth_registered()
        assert not self._actions_registered()
        assert self._blueprints_registered(app)
        assert not self._commands_registered(cli)
        assert not self._validators_registered()
        assert not self._config_declarations_registered(ckan_config)

    @pytest.mark.ckan_config(u"ckan.plugins", u"example_blanket_cli")
    def test_blanket_as_list(self, app, cli, ckan_config):
        """It possible to register list of items instead of dict.
        """
        assert not self._helpers_registered()
        assert not self._auth_registered()
        assert not self._actions_registered()
        assert not self._blueprints_registered(app)
        assert self._commands_registered(cli)
        assert not self._validators_registered()
        assert not self._config_declarations_registered(ckan_config)

    @pytest.mark.ckan_config(u"ckan.plugins", u"example_blanket_validator")
    def test_blanket_validators(self, app, cli, ckan_config):
        """It possible to register list of items instead of dict.
        """
        assert not self._helpers_registered()
        assert not self._auth_registered()
        assert not self._actions_registered()
        assert not self._blueprints_registered(app)
        assert not self._commands_registered(cli)
        assert self._validators_registered()
        assert not self._config_declarations_registered(ckan_config)

    @pytest.mark.ckan_config("ckan.plugins", "example_blanket_config_declaration")
    def test_blanket_config_declaration(self, app, cli, ckan_config):
        """It possible to register list of items instead of dict.
        """
        assert not self._helpers_registered()
        assert not self._auth_registered()
        assert not self._actions_registered()
        assert not self._blueprints_registered(app)
        assert not self._commands_registered(cli)
        assert not self._validators_registered()
        assert self._config_declarations_registered(ckan_config)

    def test_blanket_must_be_used(self, app, cli, ckan_config):
        """There is no accidental use of blanket implementation if module not
        loades.

        """
        assert not self._helpers_registered()
        assert not self._auth_registered()
        assert not self._actions_registered()
        assert not self._blueprints_registered(app)
        assert not self._commands_registered(cli)
        assert not self._validators_registered()
        assert not self._config_declarations_registered(ckan_config)
