# -*- coding: utf-8 -*-

import logging

from nose.tools import assert_raises

from ckan.lib.cli import UserCmd
import ckan.tests.helpers as helpers

log = logging.getLogger(__name__)


class TestUserAdd(object):

    '''Tests for UserCmd.add'''

    @classmethod
    def setup_class(cls):
        cls.user_cmd = UserCmd('user-command')

    def setup(self):
        helpers.reset_db()

    def test_cli_user_add_valid_args(self):
        '''Command shouldn't raise SystemExit when valid args are provided.'''
        self.user_cmd.args = ['add', 'berty', 'password=password123',
                              'fullname=Berty Guffball',
                              'email=berty@example.com']
        try:
            self.user_cmd.add()
        except SystemExit:
            assert False, "SystemExit exception shouldn't be raised"

    def test_cli_user_add_no_args(self):
        '''Command with no args raises SystemExit.'''
        self.user_cmd.args = ['add', ]
        assert_raises(SystemExit, self.user_cmd.add)

    def test_cli_user_add_no_fullname(self):
        '''Command shouldn't raise SystemExit when fullname arg not present.'''
        self.user_cmd.args = ['add', 'berty', 'password=password123',
                              'email=berty@example.com']
        try:
            self.user_cmd.add()
        except SystemExit:
            assert False, "SystemExit exception shouldn't be raised"

    def test_cli_user_add_unicode_fullname_unicode_decode_error(self):
        '''
        Command shouldn't raise UnicodeDecodeError when fullname contains
        characters outside of the ascii characterset.
        '''
        self.user_cmd.args = ['add', 'berty', 'password=password123',
                              'fullname=Harold Müffintøp',
                              'email=berty@example.com']
        try:
            self.user_cmd.add()
        except UnicodeDecodeError:
            assert False, "UnicodeDecodeError exception shouldn't be raised"

    def test_cli_user_add_unicode_fullname_system_exit(self):
        '''
        Command shouldn't raise SystemExit when fullname contains
        characters outside of the ascii characterset.
        '''
        self.user_cmd.args = ['add', 'berty', 'password=password123',
                              'fullname=Harold Müffintøp',
                              'email=berty@example.com']
        try:
            self.user_cmd.add()
        except SystemExit:
            assert False, "SystemExit exception shouldn't be raised"
