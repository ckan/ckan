# encoding: utf-8

'''API functions for deleting data from CKAN.'''
from __future__ import annotations

from ckan.types.logic import ActionResult
import logging
from typing import Any, Union, Type, cast

import sqlalchemy as sqla

import ckan.lib.jobs as jobs
import ckan.logic
import ckan.logic.schema
import ckan.plugins as plugins
import ckan.lib.api_token as api_token
from ckan import authz, model
from  ckan.lib.navl.dictization_functions import validate
from ckan.lib.search import rebuild
from ckan.model.follower import ModelFollowingModel

from ckan.common import _
from ckan.types import Context, DataDict, ErrorDict, Schema

log = logging.getLogger('ckan.logic')

# Define some shortcuts
# Ensure they are module-private so that they don't get loaded as available
# actions in the action API.
ValidationError = ckan.logic.ValidationError
NotFound = ckan.logic.NotFound
_check_access = ckan.logic.check_access
_get_or_bust = ckan.logic.get_or_bust
_get_action = ckan.logic.get_action



















