# -*- coding: utf-8 -*-

import pytest

from ckan.cli.cli import ckan


@pytest.mark.usefixtures(u"clean_db")
class TestUserAdd(object):

    def test_cli_user_add_valid_args(self, cli):
        """Command shouldn't raise SystemExit when valid args are provided.
        """
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
        """Command with no args raises SystemExit.
        """
        result = cli.invoke(ckan, [u'user', u'add'])
        assert result.exit_code

    def test_cli_user_add_no_fullname(self, cli):
        """Command shouldn't raise SystemExit when fullname arg not present.
        """
        args = [
            u"user",
            u"add",
            u"berty",
            u"password=password123",
            u"email=berty@example.com",
        ]
        result = cli.invoke(ckan, args)

        assert not result.exit_code

    def test_cli_user_add_unicode_fullname_unicode_decode_error(self, cli):
        """
        Command shouldn't raise UnicodeDecodeError when fullname contains
        characters outside of the ascii characterset.
        """
        args = [
            u"user",
            u"add",
            u"berty",
            u"password=password123",
            u"fullname=Harold Müffintøp",
            u"email=berty@example.com",
        ]
        result = cli.invoke(ckan, args)
        assert not result.exit_code

    def test_cli_user_add_unicode_fullname_system_exit(self, cli):
        """
        Command shouldn't raise SystemExit when fullname contains
        characters outside of the ascii characterset.
        """
        args = [
            u"user",
            u"add",
            u"berty",
            u"password=password123",
            u"fullname=Harold Müffintøp",
            u"email=berty@example.com",
        ]
        result = cli.invoke(ckan, args)
        assert not result.exit_code
