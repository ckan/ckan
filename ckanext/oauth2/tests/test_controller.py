# -*- coding: utf-8 -*-

# Copyright (c) 2014 CoNWeT Lab., Universidad Politécnica de Madrid
# Copyright (c) 2018 Future Internet Consulting and Development Solutions S.L.

# This file is part of OAuth2 CKAN Extension.

# OAuth2 CKAN Extension is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# OAuth2 CKAN Extension is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with OAuth2 CKAN Extension.  If not, see <http://www.gnu.org/licenses/>.

from base64 import b64decode, b64encode
import unittest
import json

from mock import MagicMock
from parameterized import parameterized

from ckanext.oauth2 import controller, plugin


RETURNED_STATUS = 302
EXAMPLE_FLASH = 'This is a test'
EXCEPTION_MSG = 'Invalid'
CAME_FROM_FIELD = 'came_from'


class CompleteException(Exception):
    description = 'Exception description'
    error = 'Exception error'


class ErrorException(Exception):
    error = 'Exception error 2'


class VoidException(Exception):
    pass


class OAuth2PluginTest(unittest.TestCase):

    def setUp(self):
        # Save the response, the request and the helper functions and mock them
        self._helpers = controller.helpers
        controller.helpers = MagicMock()

        self._oauth2 = controller.oauth2
        controller.oauth2 = MagicMock()

        self._toolkit_controller = controller.toolkit
        self._toolkit_plugin = plugin.toolkit
        plugin.toolkit = controller.toolkit = MagicMock()

        self.__session = controller.session
        controller.session = MagicMock()

        self.controller = controller.OAuth2Controller()

    def tearDown(self):
        # Unmock the function
        controller.helpers = self._helpers
        controller.oauth2 = self._oauth2
        controller.toolkit = self._toolkit_controller
        controller.session = self.__session
        plugin.toolkit = self._toolkit_plugin

    def generate_state(self, url):
        return b64encode(bytes(json.dumps({CAME_FROM_FIELD: url})))

    def get_came_from(self, state):
        return json.loads(b64decode(state)).get(CAME_FROM_FIELD, '/')

    def test_callback_no_errors(self):
        oauth2Helper = controller.oauth2.OAuth2Helper.return_value

        token = 'TOKEN'
        user_id = 'user_id'
        oauth2Helper.get_token.return_value = token
        oauth2Helper.identify.return_value = user_id

        # Call the controller
        self.controller.callback()

        oauth2Helper.get_token.assert_called_once()
        oauth2Helper.identify.assert_called_once_with(token)
        oauth2Helper.remember.assert_called_once_with(user_id)
        oauth2Helper.update_token.assert_called_once_with(user_id, token)
        oauth2Helper.redirect_from_callback.assert_called_once_with()

    @parameterized.expand([
        (),
        ('/',),
        ('/', CompleteException(EXCEPTION_MSG), None, EXCEPTION_MSG),
        ('/', CompleteException(), None, CompleteException.description),
        ('/', ErrorException(EXCEPTION_MSG), None, EXCEPTION_MSG),
        ('/', ErrorException(), None, ErrorException.error),
        ('/', VoidException(EXCEPTION_MSG), None, EXCEPTION_MSG),
        ('/', VoidException(), None, type(VoidException()).__name__),
        ('/about', Exception(EXCEPTION_MSG), EXAMPLE_FLASH, EXAMPLE_FLASH)
    ])
    def test_callback_errors(self, came_from=None, exception=Exception(EXCEPTION_MSG),
                               error_description=None, expected_flash=EXCEPTION_MSG):

        # Recover function
        controller.oauth2.get_came_from = self.get_came_from

        oauth2Helper = controller.oauth2.OAuth2Helper.return_value
        oauth2Helper.get_token.side_effect = exception

        controller.toolkit.request.GET = {}
        controller.toolkit.request.GET['state'] = self.generate_state(came_from)
        if error_description is not None:
            controller.toolkit.request.GET['error_description'] = error_description
        controller.toolkit.request.params.get = controller.toolkit.request.GET.get

        # Call the controller
        self.controller.callback()

        # Check the state and the location
        controller.session.save.assert_called_once_with()
        self.assertEquals(RETURNED_STATUS, controller.toolkit.response.status_int)
        self.assertEquals(came_from, controller.toolkit.response.location)
        controller.helpers.flash_error.assert_called_once_with(expected_flash)

    @parameterized.expand([
        (),
        (None,                        None,               '/dashboard'),
        ('/about',                    None,               '/about'),
        ('/about',                    '/ckan-admin',      '/ckan-admin'),
        (None,                        '/ckan-admin',      '/ckan-admin'),
        ('/',                         None,               '/dashboard'),
        ('/user/logged_out_redirect', None,               '/dashboard'),
        ('/',                         '/ckan-admin',      '/ckan-admin'),
        ('/user/logged_out_redirect', '/ckan-admin',      '/ckan-admin'),
        ('http://google.es',          None,               '/dashboard'),
        ('http://google.es',          None,               '/dashboard')
    ])
    def test_login(self, referer=None, came_from=None, expected_referer='/dashboard'):

        # The login function will check these variables
        controller.toolkit.request.headers = {}
        controller.toolkit.request.params = {}

        if referer:
            controller.toolkit.request.headers['Referer'] = referer

        if came_from:
            controller.toolkit.request.params['came_from'] = came_from

        # Call the function
        self.controller.login()

        self.controller.oauth2helper.challenge.assert_called_once_with(expected_referer)
