# encoding: utf-8

'''API functions for adding data to CKAN.'''
from __future__ import annotations

from ckan.types.logic import ActionResult
import logging
import random
import re
import datetime
from socket import error as socket_error
from typing import Any, Union, cast

import six

import ckan.lib.plugins as lib_plugins
import ckan.logic as logic
import ckan.plugins as plugins
import ckan.logic.schema
import ckan.lib.dictization.model_dictize as model_dictize
import ckan.lib.dictization.model_save as model_save
import ckan.lib.navl.dictization_functions
import ckan.lib.uploader as uploader
import ckan.lib.mailer as mailer
import ckan.lib.signals as signals
import ckan.lib.datapreview
import ckan.lib.api_token as api_token
import ckan.authz as authz

from ckan import model
from ckan.common import _, asbool
from ckan.lib.search import rebuild
from ckan.types import Context, DataDict, ErrorDict, Schema

# FIXME this looks nasty and should be shared better
from ckan.logic.action.update import _update_package_relationship

log = logging.getLogger(__name__)

# Define some shortcuts
# Ensure they are module-private so that they don't get loaded as available
# actions in the action API.
_validate = ckan.lib.navl.dictization_functions.validate
_check_access = logic.check_access
_get_action = logic.get_action
ValidationError = logic.ValidationError
NotFound = logic.NotFound
NotAuthorized = logic.NotAuthorized
_get_or_bust = logic.get_or_bust
fresh_context = logic.fresh_context









