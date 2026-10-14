# encoding: utf-8

'''API functions for updating existing data in CKAN.'''
from __future__ import annotations

from ckan.types.logic import ActionResult
import logging
import datetime
import time
from copy import deepcopy
from typing import Any, Union, TYPE_CHECKING, cast

import ckan.plugins as plugins
import ckan.logic as logic
import ckan.logic.schema as schema_
import ckan.lib.dictization.model_dictize as model_dictize
import ckan.lib.dictization.model_save as model_save
import ckan.lib.navl.dictization_functions as dfunc
import ckan.lib.navl.validators as validators
import ckan.lib.plugins as lib_plugins
import ckan.lib.uploader as uploader
import ckan.lib.datapreview
import ckan.lib.app_globals as app_globals
from ckan.lib import files

from ckan import model
from ckan.common import _, config
from ckan.types import Context, DataDict, ErrorDict, Schema

if TYPE_CHECKING:
    import ckan.model as model_

log = logging.getLogger(__name__)

# Define some shortcuts
# Ensure they are module-private so that they don't get loaded as available
# actions in the action API.
_validate = dfunc.validate
_get_action = logic.get_action
_check_access = logic.check_access
NotFound = logic.NotFound
ValidationError = logic.ValidationError
_get_or_bust = logic.get_or_bust















