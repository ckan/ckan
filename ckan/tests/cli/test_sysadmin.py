import pytest

from ckan.tests.helpers import call_action
from ckan.cli.cli import ckan
from ckan.tests import factories


@pytest.mark.usefixtures("non_clean_db")
class TestSysadminCommand(object):

    def test_cli_sysadmin_list(self, cli):
        """Command should list all available sysdmins"""

        sysadmin1 = factories.Sysadmin()
        sysadmin2 = factories.Sysadmin()

        args = [
            "sysadmin",
            "list",
        ]
        result = cli.invoke(ckan, args)

        assert not result.exit_code, result.output

        assert f"count = {3}" in result.output  # 2 created + site user
        assert (
            f"User name={sysadmin1['name']} email={sysadmin1['email']} id={sysadmin1['id']}"
            in result.output
        )
        assert (
            f"User name={sysadmin2['name']} email={sysadmin2['email']} id={sysadmin2['id']}"
            in result.output
        )

    def test_cli_sysadmin_add(self, cli):

        user = factories.User()

        assert user["sysadmin"] is False

        args = [
            "sysadmin",
            "add",
            user["name"],
        ]
        result = cli.invoke(ckan, args)

        assert not result.exit_code, result.output

        user = call_action("user_show", id=user["id"])

        assert user["sysadmin"] is True

    def test_cli_sysadmin_add_create(self, cli):

        args = [
            "sysadmin",
            "add",
            "--create",
            "test-user-sysadmin-create",
            "email=test123@example.org",
            "password=test1234",
        ]
        result = cli.invoke(ckan, args)

        assert not result.exit_code, result.output

        user = call_action("user_show", id="test-user-sysadmin-create")

        assert user["sysadmin"] is True

    def test_cli_sysadmin_remove(self, cli):

        user = factories.Sysadmin()

        assert user["sysadmin"] is True

        args = [
            "sysadmin",
            "remove",
            user["name"],
        ]
        result = cli.invoke(ckan, args)

        assert not result.exit_code, result.output

        user = call_action("user_show", id=user["id"])

        assert user["sysadmin"] is False
