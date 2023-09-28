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

from __future__ import unicode_literals

import logging
from . import constants

from ckan.common import session
import ckan.lib.helpers as helpers
import ckan.lib.base as base
import ckan.plugins.toolkit as toolkit
from . import oauth2

from ckanext.oauth2.plugin import _get_previous_page


log = logging.getLogger(__name__)


class OAuth2Controller(base.BaseController):

    def __init__(self):
        self.oauth2helper = oauth2.OAuth2Helper()

    def login(self):
        log.debug('login')

        # Log in attemps are fired when the user is not logged in and they click
        # on the log in button

        # Get the page where the user was when the loggin attemp was fired
        # When the user is not logged in, he/she should be redirected to the dashboard when
        # the system cannot get the previous page
        came_from_url = _get_previous_page(constants.INITIAL_PAGE)

        self.oauth2helper.challenge(came_from_url)

    def callback(self):
        try:
            token = self.oauth2helper.get_token()
            user_name = self.oauth2helper.identify(token)
            self.oauth2helper.remember(user_name)
            self.oauth2helper.update_token(user_name, token)
            self.oauth2helper.redirect_from_callback()
        except Exception as e:

            session.save()

            # If the callback is called with an error, we must show the message
            error_description = toolkit.request.GET.get('error_description')
            if not error_description:
                if e.message:
                    error_description = e.message
                elif hasattr(e, 'description') and e.description:
                    error_description = e.description
                elif hasattr(e, 'error') and e.error:
                    error_description = e.error
                else:
                    error_description = type(e).__name__

            toolkit.response.status_int = 302
            redirect_url = oauth2.get_came_from(toolkit.request.params.get('state'))
            redirect_url = '/' if redirect_url == constants.INITIAL_PAGE else redirect_url
            toolkit.response.location = redirect_url
            helpers.flash_error(error_description)
