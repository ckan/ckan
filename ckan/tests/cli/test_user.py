# -*- coding: utf-8 -*-
import pytest

from ckan.cli.user import add_user
from ckan.cli.cli import ckan


@pytest.mark.usefixtures(u"clean_db")
class TestUserAdd(object):

    def test_cli_user_add_valid_args(self, cli):
        """Command shouldn't raise SystemExit when valid args are provided."""
        args = [
            u"user",
            u"add",
            u"berty",
            u"password=password123",
            u"fullname=Berty Guffball",
            u"email=berty@example.com",
        ]
        result = cli.invoke(ckan, args)

        assert result.exit_code == 0

    def test_cli_user_add_no_args(self, cli):
        """Command with no args raises SystemExit."""
        result = cli.invoke(add_user)
        assert result.exception
        assert u"Missing argument" in result.output

